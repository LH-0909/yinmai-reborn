from pathlib import Path
from PIL import Image
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum'
im=Image.open(P/'references/20261021/06-customize.png')
im.crop((214,30,559,153)).save(A/'customize-mobile-title.png')
im.crop((478,123,950,553)).save(A/'customize-mobile-main.png')
im=Image.open(P/'references/20261021/01-home.png');im.crop((58,20,111,72)).save(A/'brand-symbol.png')
print('Clean mobile art regions prepared.')
