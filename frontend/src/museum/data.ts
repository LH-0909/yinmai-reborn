export const eras=['全部','先秦印','秦汉印','魏晋印','隋唐印','宋元印','明清印','近现代']
export const eraCounts=['12,580','1,024','2,348','986','1,120','1,864','3,215','1,023']
export const styles=['秦篆','汉印','唐印','明清','现代']
export const materials=['青田石','寿山石','和田玉','鸡血石','铜鎏金']
export const shapes=['方章','圆章','长方章','椭圆章','随形章']
export const knobs=['无钮','蟠龙','瑞兽','云纹','莲花','山水','回纹']
export const inspirations=['山河永固','知行合一','清风明月','万物生长','大美中华','宁静致远','厚德载物','海纳百川','云起龙骧','松风雅集','天行健','江山如画']
export const catalogSeed=[
 ['han-01','汉委奴国王印','秦汉','西汉','铜质','2.3 × 2.3 × 2.1 cm'],
 ['han-02','广陵王玺','秦汉','西汉','玉质','2.1 × 2.1 × 2.5 cm'],
 ['han-03','长乐未央','秦汉','西汉','铜质','2.4 × 2.4 × 2.0 cm'],
 ['wei-01','建安之印','魏晋','魏','石质','2.6 × 2.6 × 2.8 cm'],
 ['tang-01','大唐开元之宝','隋唐','唐','铜质','3.1 × 3.1 × 3.4 cm'],
 ['qing-01','乾隆御览之宝','明清','清','玉质','3.8 × 3.8 × 4.2 cm'],
 ['qing-02','鼎藏之宝','明清','清','铜质','3.0 × 3.0 × 3.3 cm'],
 ['yuan-01','赵孟頫印','宋元','元','青田石','2.2 × 2.2 × 2.6 cm'],
 ['han-04','新莽大守印','秦汉','东汉','石质','2.5 × 2.5 × 3.2 cm'],
 ['qing-03','西泠八家之印','明清','清','青田石','2.8 × 2.8 × 3.1 cm']
].map((r,i)=>({id:r[0]!,name:r[1]!,era:r[2]!,period:r[3]!,material:r[4]!,size:r[5]!,image:'catalog-'+i,image_url:'/assets/museum/catalog-'+i+'.png',provenance:'user_supplied_ui_reference',historical_metadata_verified:false}))
export type CatalogItem=typeof catalogSeed[number]
