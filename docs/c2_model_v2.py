"""C-2 testbed v2 — modality independence restored (the 2.5%->92.8% lever).
Each modality transduces its OWN aspect of the concept: modality m winds
the character stream under its own rate set and stride (physical analog:
different senses extract different features of the same experience).
Vote variants: plurality and margin-weighted (winner strength).
"""
import numpy as np
D=7; K_MASK=4
def encode(word, jitter=0.0, drop_mod=None, rng=None):
    ph = np.zeros(6)
    for m in range(6):
        rates = 1.0 + 0.7*m + 0.13*np.arange(1,4)          # modality-own rates
        s = word[m%len(word):] + word[:m%len(word)]        # modality-own stride/view
        acc = 0.0
        for i,ch in enumerate(s):
            acc += ((ord(ch)*(m+3)) % 89)/89.0 * rates[i%3]
        ph[m] = 2*np.pi*acc
    if jitter>0 and rng is not None: ph = ph + rng.normal(0,jitter,6)
    v = np.exp(1j*ph)
    if drop_mod is not None: v[drop_mod]=0.0
    return np.concatenate([v,[1.0+0j]])
def neuron_profiles(N):
    r = np.arange(N)/N*2*np.pi
    gains = 0.5+0.5*np.cos(r[:,None]+np.arange(D)[None,:]*2*np.pi/D)
    order = np.argsort(-gains,axis=1); masks=np.zeros((N,D))
    for n in range(N): masks[n,order[n,:K_MASK]]=1.0
    return gains*masks
def run(C=100,N=64,jitter=0.5,trials=400,seed=7,label=""):
    rng=np.random.default_rng(seed)
    words=[f"c{idx}w{(idx*37)%91}" for idx in range(C)]
    prof=neuron_profiles(N)
    stored=np.stack([encode(w) for w in words])
    B=prof[:,None,:]*stored[None,:,:]
    sh=np.zeros(N); pop=0; wpop=0; unan=0
    for _ in range(trials):
        c=rng.integers(C)
        cue=encode(words[c],jitter=jitter,drop_mod=int(rng.integers(6)),rng=rng)
        q=prof*cue[None,:]
        S=np.abs(np.einsum('nd,ncd->nc',np.conj(q),B))
        v=S.argmax(1); sh+=(v==c)
        pop+= (np.bincount(v,minlength=C).argmax()==c)
        Ssort=np.sort(S,1); margin=Ssort[:,-1]-Ssort[:,-2]
        w=np.zeros(C); np.add.at(w,v,margin); wpop+=(w.argmax()==c)
        unan+=(len(np.unique(v))==1)
    print(f"{label} N={N} C={C} jit={jitter}: single mean {sh.mean()/trials:.3f} best {sh.max()/trials:.3f} | plurality {pop/trials:.3f} | margin-vote {wpop/trials:.3f} | unanimity {unan/trials:.3f}")
if __name__=="__main__":
    run(N=1,jitter=0.0,label="1-neuron clean")
    run(N=1,jitter=0.5,label="1-neuron degraded")
    for j in (0.3,0.5,0.8,1.1):
        run(N=64,jitter=j,label="64n")
    run(N=256,jitter=0.8,label="256n")
    run(C=100,N=1024,jitter=0.8,trials=300,label="1024n (era scale)")
