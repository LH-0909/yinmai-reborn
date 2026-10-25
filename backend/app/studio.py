"""Local single-user studio: reference art, real favourites and native composition.

Reference art is never counted as a historical collection or an AI output.
"""
import hashlib
import io
import json
import math
from pathlib import Path
import uuid
from fastapi import APIRouter, HTTPException
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
from pydantic import BaseModel,Field
from sqlalchemy import String,JSON,select,func
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base,Session,now,ROOT,Seal,Artifact,Event
from .fontlab import source_font,render_char

router=APIRouter(prefix='/api/studio',tags=['local studio'])
CATALOG=[
    {'id':'han-01','name':'汉委奴国王印','era':'秦汉','period':'西汉','material':'铜质','size':'2.3 × 2.3 × 2.1 cm','image':'catalog-0'},
    {'id':'han-02','name':'广陵王玺','era':'秦汉','period':'西汉','material':'玉质','size':'2.1 × 2.1 × 2.5 cm','image':'catalog-1'},
    {'id':'han-03','name':'长乐未央','era':'秦汉','period':'西汉','material':'铜质','size':'2.4 × 2.4 × 2.0 cm','image':'catalog-2'},
    {'id':'wei-01','name':'建安之印','era':'魏晋','period':'魏','material':'石质','size':'2.6 × 2.6 × 2.8 cm','image':'catalog-3'},
    {'id':'tang-01','name':'大唐开元之宝','era':'隋唐','period':'唐','material':'铜质','size':'3.1 × 3.1 × 3.4 cm','image':'catalog-4'},
    {'id':'qing-01','name':'乾隆御览之宝','era':'明清','period':'清','material':'玉质','size':'3.8 × 3.8 × 4.2 cm','image':'catalog-5'},
    {'id':'qing-02','name':'鼎藏之宝','era':'明清','period':'清','material':'铜质','size':'3.0 × 3.0 × 3.3 cm','image':'catalog-6'},
    {'id':'yuan-01','name':'赵孟頫印','era':'宋元','period':'元','material':'青田石','size':'2.2 × 2.2 × 2.6 cm','image':'catalog-7'},
    {'id':'han-04','name':'新莽大守印','era':'秦汉','period':'东汉','material':'石质','size':'2.5 × 2.5 × 3.2 cm','image':'catalog-8'},
    {'id':'qing-03','name':'西泠八家之印','era':'明清','period':'清','material':'青田石','size':'2.8 × 2.8 × 3.1 cm','image':'catalog-9'},
    {'id':'great-han','name':'大汉受命玺','era':'秦汉','period':'西汉','material':'寿山石·田黄','size':'边长6.8厘米 · 通高8.9厘米','image':'detail-main-art'}]
for item in CATALOG:
    item.update(provenance='user_supplied_ui_reference',historical_metadata_verified=False,
                image_url='/assets/museum/'+item['image']+'.png')


class StudioFavorite(Base):
    __tablename__='studio_favorites'
    item_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=now)


class StudioSetting(Base):
    __tablename__='studio_settings'
    key:Mapped[str]=mapped_column(String(80),primary_key=True)
    value:Mapped[dict]=mapped_column(JSON)


class StudioDesign(Base):
    __tablename__='studio_designs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    title:Mapped[str]=mapped_column(String(120))
    parameters:Mapped[dict]=mapped_column(JSON)
    source_kind:Mapped[str]=mapped_column(String(40))
    seal_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=now)


def design_json(d):
    return {'id':d.id,'title':d.title,'parameters':d.parameters,'source_kind':d.source_kind,
            'seal_id':d.seal_id,'created_at':d.created_at.isoformat()+'Z'}


@router.get('/catalog')
def catalog(q:str='',era:str='',material:str='',sort:str='default'):
    rows=[dict(r) for r in CATALOG if (not q or q in r['name']+r['era']+r['period']+r['material'])
          and (not era or era==r['era']) and (not material or material in r['material'])]
    if sort=='name':rows.sort(key=lambda r:r['name'])
    elif sort=='reverse':rows.reverse()
    return {'items':rows,'total':len(rows),'provenance':'user_supplied_ui_reference',
            'notice':'图示内容来自用户提供的UI参考，不是已核实的馆藏目录。'}


@router.get('/state')
def state():
    with Session() as db:
        profile=db.get(StudioSetting,'profile')
        designs=list(db.scalars(select(StudioDesign).order_by(StudioDesign.created_at.desc()).limit(100)))
        return {'favorites':list(db.scalars(select(StudioFavorite.item_id))),
            'designs':[design_json(d) for d in designs],
            'profile':profile.value if profile else {'name':'山河未阑','bio':'以印为媒，连接传统与未来。','local_profile':True},
            'counts':{'designs':db.scalar(select(func.count()).select_from(StudioDesign)),
                      'favorites':db.scalar(select(func.count()).select_from(StudioFavorite)),
                      'seals':db.scalar(select(func.count()).select_from(Seal)),
                      'ai_outputs':db.scalar(select(func.count()).select_from(Artifact).where(Artifact.kind=='generated_glyphs'))},
            'mode':'single_user_local_workspace','payments_enabled':False,'public_publishing_enabled':False}


class FavoriteBody(BaseModel):
    selected:bool


@router.put('/favorites/{item_id}')
def favorite(item_id:str,body:FavoriteBody):
    if item_id not in {r['id'] for r in CATALOG}:raise HTTPException(404,'图示条目不存在')
    with Session() as db:
        row=db.get(StudioFavorite,item_id)
        if body.selected and not row:db.add(StudioFavorite(item_id=item_id))
        elif not body.selected and row:db.delete(row)
        db.add(Event(id=str(uuid.uuid4()),seal_id=None,action='studio_favorite',details={'item_id':item_id,'selected':body.selected,'item_provenance':'user_supplied_ui_reference'}))
        db.commit()
    return {'item_id':item_id,'selected':body.selected,'persisted':'MySQL'}


class ProfileBody(BaseModel):
    name:str=Field(min_length=1,max_length=40)
    bio:str=Field('',max_length=200)


@router.patch('/profile')
def profile(body:ProfileBody):
    if not body.name.strip():raise HTTPException(422,'昵称不能为空')
    value={'name':body.name.strip(),'bio':body.bio.strip(),'local_profile':True}
    with Session() as db:
        row=db.get(StudioSetting,'profile')
        if row:row.value=value
        else:db.add(StudioSetting(key='profile',value=value))
        db.commit()
    return value


class SaveDesign(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    parameters:dict
    seal_id:str|None=None


@router.post('/designs',status_code=201)
def save_design(body:SaveDesign):
    if len(json.dumps(body.parameters,ensure_ascii=False))>16000:raise HTTPException(422,'方案参数过大')
    with Session() as db:
        if body.seal_id and not db.get(Seal,body.seal_id):raise HTTPException(422,'关联作品不存在')
        d=StudioDesign(id=str(uuid.uuid4()),title=body.title,parameters=body.parameters,
            source_kind='parameter_draft',seal_id=body.seal_id)
        db.add(d);db.commit();return design_json(d)


class Compose(BaseModel):
    text:str=Field(min_length=1,max_length=12)
    layout:str=Field('square',pattern='^(square|vertical|horizontal)$')
    polarity:str=Field('zhu',pattern='^(zhu|bai)$')
    ink:str=Field('#b82e25',pattern=r'^#[0-9a-fA-F]{6}$')
    border:bool=True
    stroke_px:int=Field(0,ge=0,le=8)
    requested_style:str=Field('',max_length=40)
    material:str=Field('',max_length=40)
    creative_prompt:str=Field('',max_length=200)


@router.post('/compose',status_code=201)
def compose(body:Compose):
    # This is explicit standard-font typesetting, never represented as a trained
    # seal-style model. Decorative lion knobs remain supplied reference art.
    if not all(0x3400<=ord(c)<=0x9fff or 0x20000<=ord(c)<=0x323af for c in body.text):
        raise HTTPException(422,'规范字排版仅接受1至12个汉字')
    try:
        font=source_font()
        glyphs=[render_char(font,c,128) for c in body.text]
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,str(exc))
    image=Image.new('RGB',(512,512),'#f5efdf');draw=ImageDraw.Draw(image)
    mask=Image.new('L',(512,512),0);md=ImageDraw.Draw(mask)
    if body.border:md.rectangle((24,24,488,488),outline=255,width=10)
    n=len(glyphs)
    cols=1 if body.layout=='vertical' else n if body.layout=='horizontal' else math.ceil(math.sqrt(n))
    rows=math.ceil(n/cols);cellw=420/cols;cellh=420/rows
    for i,glyph in enumerate(glyphs):
        # Right column first, top to bottom: explicit layout convention.
        col=cols-1-i//rows;row=i%rows
        width=max(1,int(cellw));height=max(1,int(cellh))
        ratio=min(width/glyph.width,height/glyph.height)
        glyph=glyph.resize((max(1,round(glyph.width*ratio)),max(1,round(glyph.height*ratio))),Image.Resampling.LANCZOS)
        mask.paste(glyph,(46+int(col*cellw)+(width-glyph.width)//2,46+int(row*cellh)+(height-glyph.height)//2))
    if body.stroke_px:
        mask=mask.filter(ImageFilter.MaxFilter(2*body.stroke_px+1))
    image.paste(Image.new('RGB',image.size,body.ink),(0,0),mask)
    buf=io.BytesIO();image.save(buf,'PNG');data=buf.getvalue()
    from .main import save_artifact,seal_json,event
    with Session() as db:
        seal=Seal(id=str(uuid.uuid4()),title=body.text,filename='typeset-'+body.text+'.png',
                  sha256=hashlib.sha256(data).hexdigest(),source_kind='native_typeset')
        db.add(seal);db.flush()
        details={'engine':'Pillow standard Chinese glyph layout','ai_inference':False,'task':'native_typesetting',
            'text':body.text,'layout':body.layout,'polarity_requested':body.polarity,'ink':body.ink,
            'border':body.border,'stroke_px':body.stroke_px,
            'requested_style':body.requested_style,'style_model_applied':False,'material_preview':body.material,
            'content_font_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'source_kind':'native_typeset',
            'historical_authenticity_verified':False,'height':512,'width':512,
            'limitation':'规范字体排版；没有学习秦篆或汉印印风，不生成狮钮模型。'}
        details.update(polarity_applied='zhu',purpose='canonical stroke source for typesetting and geometry')
        original=save_artifact(db,seal,'original',data,details=details)
        preview=original
        if body.polarity=='bai':
            filled=Image.new('L',mask.size,0)
            ImageDraw.Draw(filled).rectangle((24,24,488,488),fill=255)
            print_mask=ImageChops.subtract(filled,mask)
            impression=Image.new('RGB',image.size,'#f5efdf')
            impression.paste(Image.new('RGB',image.size,body.ink),(0,0),print_mask)
            output=io.BytesIO();impression.save(output,'PNG')
            preview=save_artifact(db,seal,'ink_preview',output.getvalue(),details={**details,
                'polarity_applied':'bai','purpose':'actual white-character ink impression',
                'source_artifact_id':original.id})
        event(db,seal.id,'native_typesetting',details)
        d=StudioDesign(id=str(uuid.uuid4()),title=body.text,parameters=body.model_dump(),source_kind='native_typeset',seal_id=seal.id)
        db.add(d);db.commit();db.refresh(seal)
        from .main import artifact_json
        return {'seal':seal_json(seal),'design':design_json(d),'preview_url':artifact_json(preview)['url'],
                'preview_polarity':body.polarity,'ai_inference':False,'style_model_applied':False}
