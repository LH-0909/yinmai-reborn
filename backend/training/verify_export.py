"""Verify our locally trained TorchScript export across two Python runtimes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True);p.add_argument('--reference',required=True)
    p.add_argument('--report',required=True);p.add_argument('--write-reference',action='store_true')
    a=p.parse_args()
    torch.set_num_threads(4)
    model=torch.jit.load(a.model,map_location='cpu').eval()
    # Numeric probe, no training/test image or business data.
    sample=np.arange(3*256*256,dtype=np.float32).reshape(1,3,256,256)%251/250.
    with torch.no_grad(): output=model(torch.from_numpy(sample)).numpy()
    assert output.shape==sample.shape and np.isfinite(output).all()
    assert output.min()>=0 and output.max()<=1
    report={'torch':torch.__version__,'model_sha256':hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),
            'shape':list(output.shape),'finite':True,'range':[float(output.min()),float(output.max())],
            'reference_written':bool(a.write_reference),'business_model_enabled':False}
    if a.write_reference:
        np.save(a.reference,output)
    else:
        reference=np.load(a.reference,allow_pickle=False)
        report['max_absolute_difference']=float(np.max(np.abs(reference-output)))
        report['allclose_atol_1e-5']=bool(np.allclose(reference,output,atol=1e-5,rtol=1e-5))
        assert report['allclose_atol_1e-5'],'Cross-runtime inference mismatch'
    Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
