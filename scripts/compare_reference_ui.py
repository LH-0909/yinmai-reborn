"""Normalize the IAB's Windows zoom padding, retain raw images, compare pixels."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];E=P/'evidence/ui-20261021';results=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for ref in sorted((P/'references/20261021').glob('*.png')):
    raw=E/(ref.stem+'.jpg')
    if not raw.exists():continue
    im=Image.open(raw).convert('RGB');original_size=im.size
    # Browser DOM independently confirmed 1672x941. The IAB pads right/bottom
    # when Windows browser zoom is 79%. No pixels of the rendered page removed.
    actual=im.crop((0,0,1672,941));actual.save(E/(ref.stem+'.png'))
    source=Image.open(ref).convert('RGB');a=np.asarray(actual,dtype=float);b=np.asarray(source,dtype=float)
    mae=float(np.abs(a-b).mean());rmse=float(np.square(a-b).mean()**.5)
    pair=Image.new('RGB',(2000,600),'#131713');pair.paste(source.resize((1000,563)),(0,37));pair.paste(actual.resize((1000,563)),(1000,37))
    d=ImageDraw.Draw(pair);d.text((20,6),ref.stem+' | supplied reference',font=font,fill='#edd3a0');d.text((1020,6),'Native Web implementation | actual screenshot',font=font,fill='#edd3a0');pair.save(E/(ref.stem+'-compare.jpg'),quality=93)
    results.append({'page':ref.stem,'reference':[1672,941],'dom_viewport':[1672,941],'raw_capture':list(original_size),'normalization':'crop Windows/IAB right/bottom padding; no scaling','mean_absolute_rgb_error':round(mae,3),'root_mean_square_rgb_error':round(rmse,3),'exact_pixel_match':bool(np.array_equal(a,b))})
(E/'pixel-comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False))
