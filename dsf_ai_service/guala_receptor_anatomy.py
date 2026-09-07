"""Immutable physical receptor anatomy for the lean Guala runtime boundary."""

from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import zlib

import guala_core


ANATOMY_SCHEMA = "guala.native.exact_joint_source_episode.v2"
ANATOMY_SHA256 = "3dc6aee5404d43a3e417b5953ca8ae04369d7cb197a02143af260350150b0037"
ANATOMY_BYTES = 98_020
PORT_COUNT = 220
SOURCE_SAMPLE_COUNT = 880
OCCURRENCE_COUNT = 1
OCCURRENCE_FRAME_COUNT = 4
PORT_GROUP_WIDTHS = (27, 108, 2, 16, 16, 28, 5, 8, 4, 4, 2)

# The original 27 learned sight-port identities remain first. The appended 108
# fine retinal sites are unlearned. Every other physical organ is unchanged.
# This fixed zero-signal declaration is anatomy, not experience or meaning.
_COMPRESSED_BASE85 = b"""
c-rmVhkx6~6$kLMmYu|Q>^OGf5hu>-gi1`39qCA$w3%(vy;zt$Nk~9~0Z7?$_uhN&z4zXG@4frS^a0eOeY(S|_(b*ddHVSGvB(2N
>b^V>?~bHyyyd1l@3_9=Oo$U=z8}V+)lHLDzuAkDj@6RQI80^B3OivhX)lT5>px=o>wsv6Y0FxSGT70|`srNQlzRtPrpc*_)lA~b
gqRd?VTY*92)NvDci`KjB9*<Ulke4)&0Y%ML}?nfqOjAHwwO!9!5v8E*6zc~9;uv@sf6v;?Q&em)3A%x??gQ-OZq9arZSd`dE@M&
EyO{QMe`l_F~ug~++5U=)}lQjEPIDI_n+g#?^pE4Y#c4hS@`|ozeXlIS&}Zz-q4WuKx5Xh8{N2{HL^ysDAR@mH#G%2!fyyaWu==2
m(Ka;8QL9PyQ|$Ft}3Tvt8{GEq1BlvspF`09M+-LnJlT}s&rh|q1BlxspF}1Jl3JrnJ%g0t8{$Uq1BlwsS~Jl0@k6`*;!Jjs?w>l
4z13vk~%e&PK|YFb<Q*E*u&MR&DH3Z>6~9u$5!cZHA<{=K}j7)rNh-IvCi(2I<88Gt5IT|JtcKKl@3><#5#LR>i8-hu11M<E-a}N
sC2j*CDz$jQm3lY;cApvXMahZno5VOQDU8o%sS3+HR^CRx@9^CO6u4u9j-=+buKQc<EV7F8YR{_SW?GT>2NhltaGTOj;GS$YLr;#
l9D>UN{6daVx3D%>I5nsu11M<4wuxas&u#-CDu7oQm3ZU;cApv=jcW{2bVkEDt`a7U$8qPimO*wu~#lL7cJK@9G9)<;(C>s>oOdd
qvzrRmYC}}j?2|^aYakabvcg9({pi&OU!izj?33`am`E2bppo~=()HECg!>l$5qvHaaByrbrp`Qrsv`^nV9Qp99Lb>Rc9_*u4^{p
I;1X>H=5Sixm+jnyaqAYwMa1A0LC*L#9;SAf;k2-p4%V>yEhWdHGuK#1~J%ukYJtxjORCq!S0I$^9^7;!$AyoKO|US0OL6hVzB!o
!Kwx@p5-70vr3oEwqkYJ=GEn`<(kED*?KOn!HBsYfa7xXTwH+>b5(F$uAYnQFJdkm$K~m{xcVaIa&TO}o{MWQVlEfQ73jIR@*?K)
a9mYA7uQ|HTt1Ggrsv|-Wn!)X$5q#J@#-=$SGDvsl&xA_wt01Vi@|D0FxvpeGaJNUbtIT$0OPq0Vz37y!CV6v&u$QdJqQWr8Nhgc
gBa|=NHE_3#xoqmU=Klp1qLvl;~)mR4hdE@fblE`G1x;(m(7l1b=l$7<*ns<7>>)<b8!tu%=K^_m!s$63XGWR5jZYa&&Bl@G1v7t
E>F+J)fX|>BXL~5o{MWQVy;KwxB@*FS6;+iH{iIcdM>WJh`DaWan<x(yt+)x^=KSdUC+g<%fwudDLoD4s8*L9UR~Z|u$z!zwgHT1
Hi*G)MuIs8FrM2W2D=3b<{H3wc7qt~RwS5b0OR=$VzAqgV7>v2XE=z#ZbyOz1~8uEAO?FZ60B+f<5>=3u*a1yn_b1~vdgQ>Tg!C^
j?30_aScYybtjI?(Q|PHM$Gki9G9!-;`)o2>j^k6PtV2G7ctipaa_Khi)$}pt|#HR0zDU3Uc_8a#&K2kTwHe%b3FyeRnv3v>M}9c
Q*m5%Jr}Po6LUSS^fZ*KT3vQ|b$N@yo{j{w4PZR8K@9c`B$#6W<GBrDuxBE{Tmu--ZV-btkYJtxjORCq!JdT#^9^7;!$AxdBEbR!
7|(GKgPlZzRSjS~%Rvm*EL}Exiq&P0SC_YztA*pT^;}$o5pzi#m!s$63XGU*4#(x{xw!r!=9<TGd3r9czKFRNa9qBgi)$}pt_a5!
=()J^BIdda$5qvHaot7CbvKTyrsv|-Wn!)v$5q#J@#-=$SG)8yl&4x<_IP!9i@`cbFxvpeGaJNU2@=dPfbrZ0F<2J~<{H3wc7qt~
9weA&0OR=$Vz3km<{Q9xhJzR^LxKecFrMQe2J0cgss=Eg<sb&@moA%q#p<%ptIJ!<wTR=g^;}$o5p$iwaXES}uE2=7PUE;-Jr~zs
#9T`_E>F+J)fX|>8620d=i=InnCsa%u0YSll@~GBb8uW$Jr~zq#9YtCan<x(yt+)x^*kI`UC+g<%fwvIFFg(At5%nNUR~Z|uoob~
Yy%k2Y!HLJ5DDfOz<6$h80<wzFxLRavm3-<FGhlS1~8uAAO?F063jP%@eBts*h`UMfdP!?IEcYsh6Jk`z<8E}7Hmg;^+A!O^I<2-
+LjDctDDLU)a10tFToy@`8TldanVWAb{I!zWUJ9#SjwVi7&qkUX4DIFgahl_PXa-@6nNa>!|gjv9d567xXm3tf)1b9xWo6u(Wbc&
%h0M=C&Nz5s#GRdAMJZq8q=Z;t~n~2veQeYHJ8G#3<s7as~yF0v>?;onQ2k0z}KPSy;g6kqCQluZoGD^TG@jghubGHj<&|p);i7z
+jr|;l_9Ahr!bI?2GTJ=I-Va?Y=)$QoW?-98c5dw>H2kt53O{NGZ;uu1L+wc{R%%vQbO*;K>8X;-vAj@J>Pa1k_vJc1~Sk<1_sDl
y;8IJIg$+WJPc%216kEV?i9A|gC!qZ$t2ImNY*rxHIt-Qx9u8Bl1W~Gk*sSZ>n6#1#jQ9lOHxVhMo8Kl&+SYIyJDbpJlplEJS#v(
xd%gO>nLplrCad=+YgwMigGW8($P^mCd!&yaUG8-sVFbRP`Wxw*FfpjDvsm(Oi4w#4@2qcC_MvZP^kp<3Ljv}DEDJ1eI2E5psezY
9WCWWWhm`)Rwr#<o!nlI2QZGd#*tSi#|wEe2GY?$^6KPxArE38T@56!PL3Dy5C+oIK=SJ3cp)#rK>8X;UY#5-<fRzMKm*CEljDUv
jDf6bAbE9i%#ueik~NJauTG9x@+d~Ku94)`$uUbFLrB^i&+YK)<oGEs!%*5fN?x5DGv#p%rK6+d)yXkaUXG!3b(Fk1IcCZ$FqEE-
l2<3kOnCxB>FX$Yb#lCv`CBK&p*6~8(&^>hlPyTu%Pj{N)8tfT{YOv34_bL2H+*|&b-OI;Nh@hK`(5bHrE53RS+_A<6SB#$$qtl>
tunFMWV9v|C=*9z;;_kRO(sz$uFAw^lhK+?p-eoLiN_|RHJL`4_$m{hO-5@ngE9$JCIOp_)?_Ejq^dHhvdL&ocA-paDw7(UjMn75
vL^O$&1iGYNM>?A%EVTgaLqVklM7HLj>?2<#u1zBMwz%O6RsIYY_bPs;;BryW*o7}UX+QiGU1wW#3mP_Oahe&*Nh`J*@rTzs!X_M
9I?rMlu1ox!ZqWFO)e^H;tbb}4%duiCI?U^w#tNS#u1xbj52XlCR{U)*yJF}#8sJa%{XF{LnsqZWx_S%h)pg*nfNLbt{F#caw*Cr
P?>PeIAW8-D3hwnglonTn;b!z)Kn&1Gmh9~@IJZ0owmAR+z!)~PTMUOWW3si6JobGnY5Nx{uI%S7;L?J6(l?zWyAY0)=07P*W!uG
)&@`#14Iw*xFx$$4>~^Tx3ASVTVdRi3rj6IA@+&pf^6r13&(0Mgq@CzcZrqOi;K1-l}*_#9vNxanU{u}zCx^ByO_k#wXw`iix;04
e`&{3yJumqpKs8aAKsk#hxvDy`L8nY%d96;mHo6RnizgN!cUmtuQ9-bZC7@b!+xh&Ze;xJh(EdcQ6IJ=HT|?GnizgN!cT2})Mx#;
yU<V7qkg%O@wX%Xv>E?u1Accwc9K|S59jVh8`Ez``kBp-`#8U9qi6f&M#kTc_&d$`SDK#fn^8+8KPB=OX5WVF`F#*a)(qzRSuZSl
dwI6y3Qe1poszPrKD{fN)a1IGyIibYwK6Ni+@s^(Vc@=8%N@o&_4v+P7<;>6PizW1QJ=m8cCyjAJ7bRzd(wb?LWg}a>TNJRHzNjZ
48GmKr#AD<-EW8ONd3%RG%@!!<Ic-+vF?D~in1=$Q?d;mW(}B<G&>@Ou7|GdWbvT)Pv`4sS<;3}&0@uDj~Hs+v)TwuZFz~1^GTrr
*PN7d@KAs*h6BNo!D8Id?X19Vu)H?3ZPpFh_AJ{So3vfh+b*%~_-rROX?sR*dxmYtXFFNO_VBQ6n)H@OWq9gr+TCJ(E6a{gHop^B
iZF%V@5h6anxd22GCxmBR&g&|+a~YhRA${M9c(`rCjh*E_=n`LFxe;0-s~*ty=xDtIDvDsqeD9^=C4SCu9wgj^_Fb4@X)Oe?sajR
$Jpm$PnX0#K8y_=y#y!4(5drr((6T;QhUERXFCJ;;j{OE|C6rlz$r3gZyI~1B=(VE>?DQ$47)OgYDFrc_lTiw49FJ^Z(Y3VjCD7y
yYqk31%;^a$nK6h8|V&gW6(W5ymg@qpzxgCE^d&eH!YoicF_ISzos`IM4gt^?DxWsO!}GCTaamcjr^$S$u_Wr#durWEL)Iqu~=O^
P?|}*3k>;*(S_oyjgE-oM*_&&N6$tbI0IV@<72|9x|K@B>Lr%z6yFseb$hpr7o*Pdo~w7pT6b3h^<zQz<M;ugctD(oeL(CRen2Ft
R6Po&MBc*m+xa7_;oASKwhED#+<9r1-?#kSE`Q3;pBVB(M*b+tKTawC_@4aZV)BnC$v+Mw|M-Rc?f&`O%k#H0=Wm}K{4L4+tph^j
Z-2_)ZgaSpbrm9i`TDV9$y|uzMHwhW{vqfmiYFi;u7X?*xdw7A<X(__L+%5)Z}CVK;{Ff|G7EVCqyoviG4Bc&lK;v%OaQ4uYLGhQ
fshA59t?R1<T}VhArFH*9P$Xr^^iwG9tF7pawFu?kjFr7g4_(b1#&CoHpuOe$3h+lxdU=1<nfRvK%NMB66DE{r$C+xc^c&DkY_-i
328u{1qmT1Ax%gNA|Z46gA1|%i6D1D?uNvWHlzbdAYI5kkQ9<ZdXPS35poK08nOgA19>*&IgsZ<o(Fk8<OPryLS6)UG2|tXmqK0!
c{$`2kXJ%p1$i~(HIUarUI%$S<PDHFLf!;<GvqChw?f_qc{}7Ckat4f1$j5*J&^Z8-UoR<<O7foLOulfFyteUk3v2M`8ebgkWWHB
1^G1OGmy_hJ_q?c<O`55LcRp~GUO|euR^{C`8wnqkZ(f11^G7QJCN@}z6bd}<Oh%+LVg7KG2|zZpF(~H`8nhlkY7T61^G4PH;~^#
eh2wI<PVTPLjDB#GvqIjze4^7`8(tvkbgq{1^M^#_*yp_y}>vhjMnQ`4=DXPI84lXvsu{g#<JBI)UORVG&fd{S&eQ4hsRS<CL1vv
slpU?xnOyeZRMzrd1U|JjqHhaqkG>7M)<xFjPhe+80pg+jP_k6M*Ngw)K4i!{=~Y`@2-yUZkn|E#c9lJv!AAU3Da*k@-vUdT?w2e
HP)Y-3=SH~vk?2gq>}Lj
"""


@lru_cache(maxsize=1)
def receptor_anatomy() -> object:
    """Restore and verify the process-wide fixed physical receptor roster."""

    compressed = base64.b85decode(b"".join(_COMPRESSED_BASE85.split()))
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
