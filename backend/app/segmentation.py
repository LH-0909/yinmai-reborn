"""Unlabelled glyph proposals from stamp colour, frame and projection valleys.

Deterministic OpenCV, not trained character detection. Never supplies text/style
labels or automatically admits a proposal into a font training set.
"""
import io
import math
from typing import Literal
import cv2
import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, Field


class SegmentOptions(BaseModel):
    layout: str = Field('auto', pattern=r'^(auto|[1-4]x[1-4])$')
    polarity: Literal['auto','zhu','bai','black'] = 'auto'
    frame_inset: float = Field(.025, ge=0, le=.15)


def load_rgb(data):
    if not data or len(data)>15*1024*1024:
        raise ValueError('图片为空或超过15MB')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ('PNG','JPEG','WEBP') or image.width*image.height>20_000_000:
                raise ValueError('需要不超过2000万像素的PNG/JPEG/WebP')
            if min(image.size)<8: raise ValueError('图片太小，无法建议单字框')
            image=ImageOps.exif_transpose(image).convert('RGB')
            size=image.size
            image.thumbnail((1024,1024))
            return np.asarray(image),size
    except (OSError,Image.DecompressionBombError) as exc:
        raise ValueError('无法解码原图') from exc


def colour_mask(rgb, polarity):
    p=rgb.astype(np.int16)
    red=((p[:,:,0]-np.maximum(p[:,:,1],p[:,:,2]))>25)&(p[:,:,0]>65)
    is_red=red.mean()>.005
    if polarity=='black' or (polarity=='auto' and not is_red):
        gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
        if gray.std()<3: return np.zeros(gray.shape,np.uint8),'black'
        _,mask=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
        return mask,'black'
    return red.astype(np.uint8)*255,'red'


def significant_mask(mask):
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    if n<=1:return mask
    sizes=stats[1:,cv2.CC_STAT_AREA]
    threshold=max(2,round(mask.size*.00012),round(int(sizes.max())*.006))
    keep=np.zeros(n,np.uint8)
    keep[1:]=(sizes>=threshold).astype(np.uint8)*255
    cleaned=keep[labels]
    # A neighbouring seal or a red scan line must not expand the stamp region.
    h,w=mask.shape
    kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(max(3,round(w*.10)),max(3,round(h*.10))))
    grouped=cv2.morphologyEx(cleaned,cv2.MORPH_CLOSE,kernel)
    count,groups,areas,_=cv2.connectedComponentsWithStats(grouped)
    if count>1:
        main=1+int(np.argmax(areas[1:,cv2.CC_STAT_AREA]))
        cleaned=np.where(groups==main,cleaned,0).astype(np.uint8)
    return cleaned


def content_bounds(mask):
    yy,xx=np.nonzero(mask)
    if len(xx)<8:return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]


def remove_frame(mask,bounds,inset):
    x0,y0,x1,y1=bounds
    roi=mask[y0:y1,x0:x1]>0
    h,w=roi.shape
    # Trim opposite edge frame bands only. A single long stroke is not a frame.
    xp=roi.mean(0);yp=roi.mean(1)
    trim=[0,0,0,0]
    for profile,dim,left_index,right_index in [(xp,w,0,2),(yp,h,1,3)]:
        edge=max(1,round(dim*.08))
        left=np.flatnonzero(profile[:edge]>.58)
        right=np.flatnonzero(profile[-edge:]>.58)
        if len(left) and len(right):
            trim[left_index]=int(left[-1]+1)
            trim[right_index]=int(edge-right[0])
    pad_x=max(0,round(w*inset));pad_y=max(0,round(h*inset))
    x0+=max(trim[0],pad_x);x1-=max(trim[2],pad_x)
    y0+=max(trim[1],pad_y);y1-=max(trim[3],pad_y)
    if x1-x0<8 or y1-y0<8:return bounds
    return [x0,y0,x1,y1]


def cuts_for_axis(profile,parts):
    n=len(profile)
    if parts==1:return [0,n],0.
    # Search near evenly spaced cells, adapting cuts to low-ink valleys.
    smooth=cv2.GaussianBlur(np.asarray(profile,dtype=np.float32)[None,:],(0,0),max(.5,n*.008))[0]
    scale=max(float(np.quantile(smooth,.7)),.04)
    cuts=[0];gains=[]
    for i in range(1,parts):
        expected=n*i/parts
        start=max(cuts[-1]+8,int(expected-n/parts*.24))
        end=min(n-8*(parts-i),int(expected+n/parts*.24)+1)
        if end<=start:return None,-100.
        indices=np.arange(start,end)
        costs=smooth[indices]/scale+.32*((indices-expected)/(n/parts))**2
        cut=int(indices[np.argmin(costs)])
        cuts.append(cut)
        low=max(.025,min(.15,scale*.35))
        left=cut;right=cut
        while left>0 and smooth[left-1]<=low:left-=1
        while right<n-1 and smooth[right+1]<=low:right+=1
        gap=(right-left+1) if smooth[cut]<=low else 0
        valley=1.-min(float(smooth[cut])/scale,1.5)
        gains.append(.55*valley+.15*min(gap/(n/parts*.16),1.))
    cuts.append(n)
    # Extra partitions need repeated strong gaps, not just one lucky valley.
    reward=float(np.mean(gains))-.18*(parts-1)
    return cuts,reward


def rank_layouts(ink,requested):
    h,w=ink.shape
    n,_,stats,_=cv2.connectedComponentsWithStats((ink>.5).astype(np.uint8))
    components=[s for s in stats[1:] if s[cv2.CC_STAT_AREA]>=max(3,ink.size*.0015)
                and s[cv2.CC_STAT_WIDTH]>=2 and s[cv2.CC_STAT_HEIGHT]>=2]
    total=max(sum(s[cv2.CC_STAT_AREA] for s in components),1)
    def crossing(cuts,axis):
        if len(cuts)<3:return 0.
        return float(np.mean([sum(s[cv2.CC_STAT_AREA] for s in components
            if s[axis]+1<cut<s[axis]+s[axis+2]-1)/total for cut in cuts[1:-1]]))
    layouts=[tuple(map(int,requested.split('x')))] if requested!='auto' else [
        (r,c) for r in range(1,5) for c in range(1,5) if r*c<=12]
    proposals=[]
    for rows,cols in layouts:
        if h/rows<8 or w/cols<8:continue
        xc,xgain=cuts_for_axis(ink.mean(0),cols)
        yc,ygain=cuts_for_axis(ink.mean(1),rows)
        if xc is None or yc is None:continue
        aspect=abs(math.log((w/cols)/(h/rows)))
        occupied=[]
        boxes=[]
        # Columns from right to left, each top to bottom; this is a display order,
        # not a claim about the correct reading order of a historical seal.
        for col in reversed(range(cols)):
            for row in range(rows):
                b=[xc[col],yc[row],xc[col+1],yc[row+1]]
                cell=ink[b[1]:b[3],b[0]:b[2]]
                ratio=float(cell.mean())
                occupied.append(.015<ratio<.88)
                boxes.append(b)
        invalid=1.-sum(occupied)/len(occupied)
        # A cut crossing a connected glyph is weaker than an actual gap. This
        # helps distinguish two tall characters from four square characters.
        cut_penalty=crossing(xc,0)+crossing(yc,1)
        score=xgain+ygain-.85*cut_penalty-.35*aspect-.08*math.log(rows*cols)-1.4*invalid
        proposals.append({'layout':f'{rows}x{cols}','score':round(score,5),'cuts_x':xc,'cuts_y':yc,
                          'boxes':boxes,'occupied':occupied})
    return sorted(proposals,key=lambda x:x['score'],reverse=True)


def segment(data,options=None):
    options=options or SegmentOptions()
    rgb,original_size=load_rgb(data);h,w=rgb.shape[:2]
    mask,colour=colour_mask(rgb,options.polarity)
    mask=significant_mask(mask)
    bounds=content_bounds(mask)
    common={'engine':'OpenCV colour/frame/projection-v1','ai_inference':False,
        'task':'unlabelled_glyph_proposals','source_image_size':list(original_size),
        'coordinate_space':'normalized_exif_oriented_original_image_xy_0_1',
        'options':options.model_dump(),'human_review_required':True,
        'character_labels_assigned':False,'style_labels_assigned':False,'font_split_assigned':False,
        'reading_order':'right-column-first display convention; not historically verified'}
    if bounds is None:
        return {**common,'glyphs':[],'status':'no_foreground','warnings':['未找到足够清晰的印迹，请检查原图或尝试黑色字迹模式。'],
                'layout':None,'alternatives':[]}
    bounds=remove_frame(mask,bounds,options.frame_inset)
    x0,y0,x1,y1=bounds
    red_coverage=float((mask[y0:y1,x0:x1]>0).mean())
    polarity=options.polarity
    if polarity=='auto':polarity='black' if colour=='black' else ('bai' if red_coverage>.48 else 'zhu')
    ink=(mask[y0:y1,x0:x1]>0).astype(np.float32)
    if polarity=='bai':ink=1.-ink
    ranked=rank_layouts(ink,options.layout)
    warnings=['候选框不是已识别的汉字；须检查边界、朱白文及释文。']
    if options.polarity=='auto' and colour=='red':warnings.append('朱白文依据红白比例估计；残损和边框可能影响判断。')
    if not ranked:
        return {**common,'glyphs':[],'status':'too_small','warnings':['印面太小，无法按该布局切分；请改用较少行列。'],
                'layout':None,'alternatives':[],'polarity':polarity}
    best=ranked[0]
    if options.layout=='auto' and (len(ranked)>1 and best['score']-ranked[1]['score']<.1):
        warnings.append('行列判断存在歧义，可选择行列布局重新分割。')
    if best['layout']=='1x1':warnings.append('未检测到足够稳定的字间隔，保留整印候选；可指定行列或手动框选。')
    glyphs=[]
    for b,occupied in zip(best['boxes'],best['occupied']):
        if not occupied:continue
        l,t,r,bottom=b
        # All proposals remain unreviewed; do not tighten across neighbouring
        # strokes as that would erase the user's opportunity to correct a cut.
        norm=[(x0+l)/w,(y0+t)/h,(x0+r)/w,(y0+bottom)/h]
        if (norm[2]-norm[0])*original_size[0]<8 or (norm[3]-norm[1])*original_size[1]<8:continue
        glyphs.append({'char':'','box':norm,'polarity':polarity,'mirrored':False,'reviewed':False,
                       'proposal_method':'projection_grid','box_reviewed':False})
    if len(glyphs)!=len(best['boxes']):warnings.append('部分区域为空或过小，未作为字形候选导出。')
    return {**common,'glyphs':glyphs,'status':'needs_review' if glyphs else 'no_candidates',
        'warnings':warnings,'layout':best['layout'],'polarity':polarity,
        'seal_bounds':[x0/w,y0/h,x1/w,y1/h],
        'alternatives':[{'layout':r['layout'],'heuristic_score':r['score']} for r in ranked[:5]],
        'score_description':'Layout ranking heuristic, not a probability or segmentation accuracy'}
