"""Immutable physical receptor anatomy for the lean Guala runtime boundary."""

from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import zlib

import guala_core


ANATOMY_SCHEMA = "guala.native.exact_joint_source_episode.v2"
ANATOMY_SHA256 = "d0c0f483563c22589e0ee76a7033a83a6fc590634a42d2210ae47f062606c97d"
ANATOMY_BYTES = 50_508
PORT_COUNT = 112
SOURCE_SAMPLE_COUNT = 448
OCCURRENCE_COUNT = 1
OCCURRENCE_FRAME_COUNT = 4
PORT_GROUP_WIDTHS = (27, 2, 16, 16, 28, 5, 8, 4, 4, 2)

# This is the exact quiescent receptor declaration emitted by source commit
# 2fd5fb8ab76f3ccbc7a9647ca06da8579ba400d3 under task-1430's authorized
# anatomy. It is anatomy, not experience, meaning, DSF output, or a lookup
# table. Runtime signal bodies replace only its 112 x 4 physical samples.
_COMPRESSED_BASE85 = b"""\
c-rmV_j}v88315dUKzGy$B7d=iIdz&CtWTLcU;G{ch~E6-E}XOrXY(Ku7Z>k<*)At%9cb228lBn>4(pczsD8<N)%pjfFOxaz
xe#CFF)4J26;|ShmP-PF^hUbH}#@W>rvNt80~3J=%i6FBH2$&&VP1^>#&}7<|QzrmJC_nap~50B8y(>nj86ggDewxu|)JW0<
VWb2>(7JjHX`5=ZdMDGWf@1%;|Yf=u(69nKNF1s6SnXi#ZtWQ$``*%q)k5zJ^(}Vd$k=5)B!oGV0Sao_KU-5OSX+-f0MLlVx
%GeJ`Zinb9Dcu|(efHJkALvhq0cy)$|Q-yi;T6B;HF8y$VprT>G(q-%6zf0%TWZgfUj*MyH+ff?Z&!n<4))A-d}zji^oDNDD
c^TVWaI)+HcK%IJZ8YOj1k&cNv_3A8_)UiZ57V6Zivr<yW7U|fiQ?JfyNu8!hr-?fC>a3O2X^C`Ns8g@bdP$wONT-cD_3GRx
snZeZbWo>WotwovM!q#_U~BZ9>D(%*V~BLHHCnUI?UFjCNC#V^HS27Y)UiZ5*cz=_XS1Y^Ez-f(Xw5oXC3Tu29c+!(taGQNP
D`YNt<jowwoB@?MLO6TtyyQMq)tbqgRRk;b?z4HnEBSIiLKFhrn6g8#}MgYYqVyadnI*Dkq)*-Yu346QpXbMU~9ByoxPGewn
ztCqc!V1D5=vF>0oQLW}Sy6by^}FY>n2evtLrDEz-f(Xw5nYC3QL?9c+!(tHUn^g>M|OQz!J2K%)-RVn!1nqN{|zf;pD?KQQ
kh2_qIbzW0Xqy76F?c&_7j>1)?Z9geU&n|=ZWY}B%`!1L)#MFnn53f#Z~ub{viR~PsWY-ikoPaRFyPMol(>H6}dwr^e}vMen
-_u|qpWmM}k_{y+h8EJv%``&=E^vx>i=<u_bpKJ0_x_DDH$voXwUCe=w`SfKKM?>OhNFCRR(X@{3HbT|~xuODTN+8VwNYie%
bORylf?QRBv?P#L0i@MDHgVHhALN<}q%DE83m}_1?j!4jTvvf?N+6pBkgc}eG)#o73-X2vWJ?0sDuC=9>m394k+nhIRDo<uA
lp*Nbz&Gzu*7X^ZIZWCBs&txPLZU2Y#1GstWEN^isZ3G^0-LyShsZ3Ldm)$Hxwj|tIzE;h@lrynzmutZ9FSb8|9`7r6Hp<3M
ehzZW+xMQr1Per9x@SD9s|uj-^|sjg)m!-cg~nWRz9`rQOj@v)M$-x+u3*C~X;~T|n8=_13YD8`#<?cT^~wGRkHFWgE}f)k}
G|45jf_@1%jflZ)lJtKw)#9I<zDzL57+AWaD*_D;?h^1ceBC4t1=$@xO=sX*EiNbH@QFXRIi$fg7mdne}$`A`M2C4t1=$@xO
=t3b9Tkk~spXUPK<$&N%4dne~C`A9|bSR#qNlXI4QtRQJzeQpPPC+AQ3M1|6jQDX1poGA}gC`}n9_D;^3@~H}?C8NaN$vIO#
Q=znFl-N5tXUgX)lua2W_D;^1lHWQ>_NJ6>6sEj*k^!YDw;aEekLI&C$(ML3)gsp&#!#H27gy=bWQHjYn&eHEluX29_@GI(C
JiMM@yI=BQmx6dl8Jb{9yF=eWJSqDJW3CmRBN)TWFj7$2TiIqSyM6*kH~{2)tam;nTW^XL6d4tZYY_EN8dq{YE5pIHIa<DgC
^CQ+)^?TkF<j()tcN^G7*ojgC^CQY$%zCN7X@-YE3qkOvGd9ph>kRTS_M45p>X`T9Z3UCgO2((4<<EZ6y=&XgO$7t;vp(iFk
}0G^y6)Zdnt_$T(<Ht;w#EiFiC5G^y6)o|1`p6dW|E*5tmDiFoWAG^y5PPsv0);tiTqYw|$JL_E$7npA7@P{~9*x(%9CYqGC
oA|BHQO{z6HP%;sZWP>KvnvCz08!xmLJAUA>i$dEV1L{wTut7G+Nz@x%j61YO#<@2pAkJ$q$<KpWm16O0@yL_u3KaPOk-~y&
H1<*`cyAcIkSA-7-=l+3k2c6QaR)TuW8rA-zzIX@-yj#M_p-EzQJ2P9&0tP=N((;v8JSK!i+m_rpK{ae;`3~z9Zl?>IO&jQ2
v76bkw4GBRLuW=0Y6Pr%0%|7Buhg0MTBn@!+%%+54JH4g{%EKIZs6VMZ{me{#x$@o|t}>WJw6Wi0~`dU+a^h9}k91yw;y5BK
{)cuNLEfP=Fr~Xc+k-dpLH_(vW@;>DR8m-urygReSsMM8sc2{Pkk|_loxRuGbUEuMnPs><h@wmw_Bi4Niwi>SU#TezxVABuz
_RQJRVm@3JH@x$NVflIf(2vogqC9rscJ_fsji<EP^Fo2MZ5qG30#g&m0x-vK+i>ewBz=ZC#qfc;#Ced488oSs`F<1_?cH1L(
{?74@56L{i1cb0_Q3&zcx<z!}q-Sd(d+EX-u0@KD!5laq8ZaNfYnE2z;f6e>Rk|=;zZq{SANpi`XlSE(&=mSDeqf7&)oX|d0
1t?<J5FCs<<8q&K0eeOFS}t!AJ7{~!cIle7Bf0GeZRcm(xTftJx$PUYouBP;8QcB5EsN6gwbFTYnRbKBrlRcpWcfn8M;r#FK
lH~3HCZ7ClpiNW6Wk}$JiLq<O=6FY^Y{G-fOqn5!mlvdCYQ5alHQtDDL;Z^vq!lZ&iEBcQ1leiymVxUg>#=eUh3>H53%3IUM
-1zn8${K9>GB|6zZuTrKy()wRgx{`3kuAFV6vgqnL(ph>Y0R#$GFleUQhF7?h_IQwFUSDumu7xjY5Pck{WktIkmO+PdrCOcx
Zq%p-Z}g;(h2@)YPE=5uGd01Er;Ap1a+zP2=fcF^}`uj%D0QP|VmVd{i58YWsgpe&e@KO!j&fW^tyw`sOyK>e(<I;$vd6vV*
54~*`ROPLNx_LcxLee|ps!V%b+<3A>5+tPJiOC!xPv;VS3-M*y$nHQeVIawHOW>H$=x*&TytPp|<aZ|NIZ09RP#HgqitPq}p
^o#t+YM2^NQVHQrZr(KG%f^rG_%5IC82BcG*Ao6XCI0vx{<s+acoP0N4F329e!D-vy`109%x|9^k0r@(9Uz3?{={#$+0V|p6
2dQEf1Guh6LOd}0}0^|L4Tg@fCzaX;sb~eAznay3*y@l-+}mUR#OT2K7<Bw1n~n19fB7lFA58Se`OBSf@ni@AdVq^2=OC`A4
B{E;v<NkLi`Nk=McYu_!#1s5Wj->1maVO&mevc@j1kAAijY3EyV92eh={nh(AJn3Go%gpCJAW@fV1{Li`Ql?-2ih_$S1_ApQ
;UABZl*e<2)*69^Zg2SFkFymCPdAUue#AzniG5CKF85uJO@=-T6YG1mWRQbC7(sCGy8QQ`!#PkY^Qd#DSmdUvu8bYl-zw^v?
5yFS!>hrukj&eh&!Eoscul<f*?%XS4d=J6bA&FU33=SGRzvm&TLD}q|on5jwDq_)H?>J76^?2$WUj2~VNgD&4HcE65b3*MdG
ZjLLUa0_YtAF{D$d;"""


@lru_cache(maxsize=1)
def receptor_anatomy() -> object:
    """Restore and verify the process-wide fixed physical receptor roster."""

    compressed = base64.b85decode(_COMPRESSED_BASE85.replace(b"\n", b""))
    raw = zlib.decompress(compressed)
    if len(raw) != ANATOMY_BYTES or hashlib.sha256(raw).hexdigest() != ANATOMY_SHA256:
        raise RuntimeError("Guala receptor anatomy asset changed")
    episode = guala_core.settle_native_joint_source_episode(
        raw,
        PORT_COUNT,
        SOURCE_SAMPLE_COUNT,
        OCCURRENCE_COUNT,
        OCCURRENCE_FRAME_COUNT,
    )
    if (
        episode.schema != ANATOMY_SCHEMA
        or episode.port_count != PORT_COUNT
        or episode.source_sample_count != SOURCE_SAMPLE_COUNT
        or episode.occurrence_count != OCCURRENCE_COUNT
        or episode.occurrence_frame_count != OCCURRENCE_FRAME_COUNT
        or episode.python_callback_count != 0
        or bytes(episode.as_bytes()) != raw
    ):
        raise RuntimeError("native core changed Guala receptor anatomy custody")
    return episode
