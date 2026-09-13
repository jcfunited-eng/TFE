"""Immutable physical receptor anatomy for the lean Guala runtime boundary."""

from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import zlib

import guala_core


ANATOMY_SCHEMA = "guala.native.exact_joint_source_episode.v2"
ANATOMY_SHA256 = "d37dc4223aac3c8ce2988c7fd7fb1b1ba95ef83baacbb03262e9fbd3d1e70384"
LEGACY_ANATOMY_SHA256 = "3dc6aee5404d43a3e417b5953ca8ae04369d7cb197a02143af260350150b0037"
ANATOMY_BYTES = 439_432
LEGACY_ANATOMY_BYTES = 98_020
PORT_COUNT = 988
LEGACY_PORT_COUNT = 220
# Stage 2 of the drive organ (2026-09-13): two body-sense interoceptors appended
# after the focal field — reserve deficit and thermal load as fractions of
# declared capacity. Built by tools/build_need_anatomy.py from the focal asset.
NEED_ANATOMY_SHA256 = "035c13a8ae471c523d2b6a9c52bfef5cdd2120cf8b3ba9bf24f3569ac998b75e"
NEED_ANATOMY_BYTES = 440465
NEED_PORT_COUNT = 990
SOURCE_SAMPLE_COUNT = 3_952
OCCURRENCE_COUNT = 1
OCCURRENCE_FRAME_COUNT = 4
PORT_GROUP_WIDTHS = (27, 108, 2, 16, 16, 28, 5, 8, 4, 4, 2, 768)

# The established220-port declaration is retained for authenticated source
# events which contain no focal coverage (including a pre-growth pending return).
# The full declaration appends768 sight identities AFTER every existing port.
# These fixed zero-signal assets are anatomy, not experience or meaning.
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


# Generated append-only asset; every old port record is byte-identical.
_FOCAL_COMPRESSED_BASE85 = b"""
c-rmV1$12X8ZGdt7ighH3beReN{)@-?(SYfI&A|nCP|^VySux)ySux?b$55+?UR<a;hxSn`;l+TTW{ZW_kv~;DD%st`R_A(viUY!
?Yz^*jp4xDvbo7UO|4B0ot2J>J<Z)M9qkPh%gwD#mGZ=fruL@pj<#vJ-v50uX!>7s3+0-dDia%~wsheG8@hTblbV{#^G|<crQ?vs
hUSje#(}v(Is9Tku5oA%zwT*k$KQ_2Rm$Bh?deB#mYcgP_?wnWrD<YIQ+snc$W5v=P5%vaOq%t3`067n<w@mA8SgjShb)yVABqoY
=xJ~1Zs_Xhso>U1xwSksy>a~1AeUPt*VQt)9sii#cWIh5sinQ#Ff|yMYX}D9{`dc3g8#nW`(u1-%hd9C{P*K86S~UnT^*Ha<2Rd7
J{UK4O$a7*w)S*Q=$g<mwOpAH;$JlwABg`#{8MJ!OEZ4;KmU)7+rw(NM^!%_Z>miv$kGX<<Et~UMx8KACzOt_&Y&7~qAZ<AI=(uC
Yt)IebYkiF>I|t-C&|)Dq~ohIv__qLmQG$ezB<Ed)G1`?6r|&;GrUHfVwO%(I=(vd*g8Sq(`ca6Xx((?tx+e)($Q(uS!cc)b;2wi
okpE?M%1ViW$EZN>Z~)eMx8iIN2gI|o%w6jNwRcw8g<rLphlg1mX1!N&N`!N)G1`?=rroAGrC5dVwR3hqs}@D+B#w1(`cyEXx(%c
s!=D%($Q(uS!dxIb;2wiokpE?7O7Du%F@wk)LCatjXH6bj!vV_I*Zn*lVs`WH0rFgSdBXQEFGOjoplzkQKyilqtmFf&e$4tidi~3
jXLX$o0HBWGw%3?-v9ouKVf%huJ_F|uVR1oYjOE<Ex~aG)wy(Db>>=<;|i;D=>Y4@wG_t{Rp-)))|qQ*jw`Otr6aC0*D@SeQk_d@
UT3alIj($lE**lMxt8O&3e~xEDt6{tp5rQ3=h89RnQH}(t5lt<BradB73ah?Ci|E?r&?p!jB~Pj4QH^GNU*>FQ?ua=wlWD88er-+
oWWKh!6E}p?S?bhsw7x!fT`bb23w5;OAIhI9L`{?lVEuROdW?a*cv2Q!2nas;SAPL^RYR|xVjwZ>T-R##&cXjbuOL3oVnKIxWejO
I)OQJHF8{0buOL1oVfyyE3VF^)0Z<>$Z;jrxpek&=88D3e046JyqvjWj;m0eOXn_Uu7u+%R_D^yWoNED$5pD%rK`)%T!orzs37a=
a-gfrbp|VvV1WUqX2Th*M1q9|n7R#Tu(e3A$N*Ej;S9Dm2^Je*>NlLh)*-<X156EvGuXN$Sl$3r$KedN9tl=3z|?X$gRNilu{q4R
x*Y22a(%fr;JAY7Tsng}b8X0Rh1I!q0(0ith~tW?bLsr$%(XGc6<6od>C2gG6OJpX&ZV=LGuNgZSH3!zPF~Jjn{ix)>RdW^Idg5!
aTTj`>FTmG*A^UCsXCXgE<1B=S#u2)W?fwlb#=MUU|W%3fdQsw!x?OA5-c>p)NMF}Z9{@Z2AJ9nXRvKau-E`ozu^qF9SN2gU}`v=
!L}#C@&=eX4rj0(NU(wdrk2AQY{#09%~8hH<w#eT>&vwh#}!oP(izN|YiEuttj?tqm^0Td99LAGOXn|Vu3b5<xH^|kU(Q^+aa>7t
E}gxcxpwEc^3}O?@^a?dgX1bx=hC^$nQKput5}^&SC^f+_Tsoo)wy(a*_mtanro;i>*{i(tIKr;+lK@T3@|kt&S3kJV4(q~Zo?UD
KN2i5z|?LygH0g8VgpS5hBMgyBv@jAso`)2Ya+q&2ADbyXRrfEuz~@mmctpWx#nYYoN;wI*45?ua!us8g6dp4gE@1RIj*oemrh{L
T$4Dis5+O<U(Q^UIj*=mmrh^KTvIr%q&k<*Ud~)C99O<Nmrh>JTnBPoh3Z^7cR6z%#Bmj?bLr}`Ggm9eRjSUVtIN(@Z8g_Wan{x4
SXY<p4AxG91qPU!4QH?p5-c>p)NMF}b&_C_0j74t8SG#ZEH=Q@Z#aWhNU+2JQ^Vm5)<uHl4KQ^a&S2dnSit~O%i#>xQ}eMo$+)_l
=<0HPxu$YlL3J*j!JN4c;kd%;Tsna{a~;ZYMb)`<{&MD;#&N~fxpew+<~oeyN~&||?B&dLILDQ*&ZU!=GuIIuSD`wW&Rx!2M{-=n
>Rh_I?96o($5pD%rK`)%Tu0YjLnT>PmlIuGt~1y%Bv@d8so8J_JC+0s4KQ^Z&S1xpV37f)cEcI$coHl&z|?OzgPlNvB?g!p4rj0v
NwB;DrjElI>?9JbV1TLR@C6%?zIl;cM`dzTdrMbaL%FHa&{-*WL9IL_m;MSLF(~~TeC$%W_Kr$hQ)|m%<%ttIr%dZ=X>MwrP(HM|
rMoFbSZMa!4*)@BT0Yht-uLza)*T+qyu$<C;r(!j51jKIJ{n(bny0jun;IG$4rpqh*wENGXy#}8$ggg!^xlTIjLS8b+q)~}hDjCt
C*uptw1&2p*4CCO<x2NqLvqDN{BKO(kDB?fYRvvpHS?WkeXaWHBjnik_CbteP{lE*>NqqPBvC0Y2+|93FasG@fea1EFi!G~fgrsg
hcJ*)70AedjFM8QFRgx%Lm9}p3S?|RCXM<t(i3tR1DRBTObp0;Ax?r&kY13(8OVGU$h-krEHxGb{Tb;7IS&I_r~+B23OOtn1PLtl
wbe~>UPiK5MY3o~#-$)AO43boK1Q-sMY3c`mKvkRFp{K~<Oo7Cm~*!?Fc&l$lwll1aY3zs8|6rbGN?uw7?e?CoDY(`D7`4>XDGvJ
l%Yjgj2fdb7Nr;E0t{tTjWRMQ<6>hNCW$D$C`U1raW%@=pv*Tm=1YzG0_#ROnxRapQ6>guL5-a+<$|?P2LE$)GSJn@Z<pgjjAKy6
QCBDDF66=tWLO1KS10E#<RT1YR0UF3C+9BY7zQ$~0;#K$a~E<^1~RDvsjHK77jiKMGG7H!S10E#<l+oup$ep~PR?b?v5aJ~ilnYi
&SlAQjAW^bq^?fRWyvK7$zaaij;>D5eaa;n%Agvhu1?Nn%B2{}uo|VVPR?b@r5Vbo8l|pI&SlDF7|OUBrLIoSWy)n4%A^{lu1?Nf
%5*xJ8#9Ztxud;1y?eT*l*`?z<@8@xIu2=^{iUbz5Bh4yjlUf;^ZmM7y2}k6&CNZXxI3q<G$)<e-WhLcl1X2a0hCFQWfI7we@zBb
CSjIID3ks*8AO>xStgN8`qyMIWfEtZ#4_n$lOdEzl4X*}q<>9@QYQH<le|p&*JK!FQphqX$fSQwhEpcRER&*4`qyNhT1|q!XU0Hh
MmLjrDU%?}L}$i+Hkpqy3A0ReX6$E^5tK=kWuh}<KbwrCOyVpPof-StWPZvd$uiNIv7b#ApiJ^vCOR|rv&ksRq>yEzGh;uSjHXPA
StdF&_Or=?wVH%|&y1nYjBX|iQ6@o_iO!7uY_c$A5@wm`%-GK+i%=#}mWj@c{cJLZGKsTHbY|>llSL_$B+Eo+#(p+gj55h*ndr>e
&nAmgCWR~$of-StWGrP;%reoLv7b$*@8qWcrW-n&THBf`U)^aVa#PB!Gw;HIxe>VoIwns0>PHa`%}syr5i>!W4sGe``!T}mSFH58
c)2BKJ%Bn|0nv@$ctg3fr5ksAOHbQM)o*TSYMoe~GHqgcU~W{dc}lr0{aH8-%~P7%+sm!Pb6?%MaPMs$m2z{rv-dNj($qe=Z2YU2
$<2D})Q(o%wXNmUwD-y9y+3KEA=|yHsk<kAhxW;R-(CED`3Kni%NzXVuI_Rr%YI0%_a?!A8{r4q@GBbdu<b0jXFlwQ<!0O{{BI-v
pl|-DZ)$7FrXP~)y-D!jM)<+s{88W4)7m+ur;`1spK+t`zm51qZ2T1r{LU%m_KwypdwlQSdz<LLjr2pm`QyGdebb!&w4ZUK@V|}t
!)*NJtUv9WTP9}756-2xi2Ym0p8g(kV`mvm?&<1o>b<vTv@Oe2xvin=kaD>@``f$To3hEP{p*&_&3e;Ut&F()k9&Z@y>wOXrq=H4
$9H;*u)l5C1HTb=NA|bx!0wpS_wK@;d)R{v>}9KAAJEc0hk9;kZu)Hk|F(e-{w9BN_p~*&wPgRv-FuU`zh&I%u{<~17wm~GU7a{j
mD_NKHB4vfsC13Z^?5t)%J#0->G%Gj>2<WOjyC+Nx%Z0M$XuVBN6x$vOl{>wbLGh$y&8DS0p&^fRKQ(~F9c(!UySSX@A(RL4wu*Z
yl+=$lWf0cJK!7IPOEM^O}2B-cHlR(J*>LzVX~cjwu5T1UA(VtrK5Ysqq6CcuhWjm&3>z7=bmi(n^-Q_RKdO9(>nc|n%+CPt(<<J
)G-rx$yx7{-p7@4S7%FQ`uk66?EvuTzW<Q)878B0Uw^l+NzXs)Q>wKC-<yr=^8r)SXC&dSFXOhB?rA}`aG!tc^xt*ww|T<;U+f_@
VlUMf8+Y_Hd{c}&b#iM*cXvxyruOLE|Gb~Uz4+HZ0)Or3EVtuZWMO|}?4dPckL`=yQNjJ$)LE|Jv{KH59+~U&J_hoFec!wHS!dGy
#=67)?{uNi((BQ6P)qw9bo;!Ip}SPy_wLmNDE`cD>-`r>`Ws89uN}1d?9b^<A4KgF8=8B%o7&4AJzWjmQ_7XLS>)q#-Q_m0H1$5-
X1!b2lyYnD#p>Qql;)1MPB5h37%h<d+B=QS_5LFPGV7&hTiWp**wm)hC30aQYHVz5=<aBU!rs5@eW}}n%B@pd+Gl*^%->AIY`>L!
_UA&if1ExcGCm>ZVLu^8_5FnCsFbrl3kK)XTSWgYrq7*>H!qZHZmLXdnA+0SlYYgVUP_L^ch21{?M)4n(yz+@^Ge6Va?{^F^Yz4L
zG2*q4@|%ImYciNFXSziO4G!a^d6qWSMRSrVz$qanI9stzGA14Vu2+VNX%F4R8lOo#6pSrik(J^MV443F<-IMNwL@xizVhOb_OYy
SYnC9e8tWr#qyR|UShstXOUtBOROL<U$L`Ev7#kbl$fvBIiy(05-Ul}SM1z5i7h&Z6Z9NQkKtb(q1Adgo1Mp+1*VyL4`;LUS+meI
Q}f|$b^&V^nP%!foXsv|&0^C`?T543MXXt3nyLSAHoKTL%bR9uK%C7kVa*DrnK}?>vrAdCqG_fU#M$gJ)~sZjsRwa3yPPx&%^oCF
58`Zg1#4#ZAfb8?XR|9=GqVQ?)q^;jUB#N2JxHh?#M$g>*39fdLiHfdX4kN0W)Bjo2XQvLmNhebkWf8{v)Og5nc0Jc>Oq{%u4m26
9wbx`;%s&UYi9N!p?VN!vl~gX$m~HP^&rk>H?d}B4-%;daW=cT_GiikSzEI}TeCWg-9m~5mY5!6&SJNcVxc9brqNmKHc~9I#MCo7
i``C&#g>>_MrW}*NU_8cQ^)8mb|)#8x5U&iI*Z*!iWMv|^^4A8cavg8OHA#ev)DbPSjiGox9BW(Z|yx*khwJrv^A@@*?p{8V4A7-
a5lT2H49BMH6PAq53pvDX{PSO+3Z2qEH=&5emI*w#F{0hnfecBvxix;ylJKe#M$f-)~sNfsRMB~dz3XRnr3Q2oXs9%%}S=3dJt!`
$4Rr$>_N0O^EP{eH8Xn<ZOy#Ro@C9;9z<I+Z?mUZGqVTL*38@NY1Yi_L9{jVHhYFOGkXwi&AiQ?WzEbUL|Zd&v*%bdvj@@E%-igF
*39fdv^DcKdx14Gdk}5Syv<%D%_6f0(bmk{>?PLB>_N0O^EP|A_Gik4SzEJETeCWgy+VowmY5!6&SI~UVxc9brqNmKHBv0H#MCo7
i@i>Y#g>>_MrW}%NU_8cQ^)8m_9iKox5U&iI*YwUiWMv|^^4A8Z<At0OHA#ev)DVNSjiGox9BYPZtXo)n7K6zwKc1^*?X*6V4A7-
a5j6NH49BMH6PAqAFyVTX{PSO+3Z8sEH=&5emI+b#F{0hnfecBvyWM`ylJKe#M$f<)~sNfsRMB~`;;{+nr3Q2oXtLC%}S=3dJt!`
&q=e;>_N0O^EUf}H8Xn<ZOy#RzQdZCJ&3ku-e%ur&CDJ|TQhI7@3CfP52CG^x7qhuGqVTL*38@N2dtUdgJ^5!ZT3Uf%<Mt5HS;$6
5o>1lAljOFoBfzIGkXwi&AiQiLYhTp52CG^x7klwGqVTL*38@NXSF|5F3Q@PMcSIxS?uSeSYV0iG3G4x3sNk!#MCr8i~W)mi!3qq
jLu@eBE@1$Of93c*sn>k#1d1-=q&adQY>$YsbO>$`z<L}u*B3aI*a{|6f0U{Y8Rcweou;(EHQP9&SHP4y{C#Yw`P&HX7x7vBWo6z
X6ikh&Hluig{GOB4`;JKvu2TLrtZVp>@TcYY?`V4a5noZYnGU1>OY*#{>GZ+O*1th&SrmS%?hTOIuK{Gf3Rjn(@ZUhv)Mmcvyy41
9>m$~U!+-R_8{7td7J&4H8Xn<ZOy#R{==G?J&3ku-e&)0&CDJ|TQhI7FIh9Q2hrBd+YE2x%*-A{TQhI70j!zXgJ^5!Z8nfKGkXwi
&AiP9v1VouqOF;?*<jYp>_N0O^EMkonnh+0qOF;?*-+NZ>_N0O^EMkcpyp@F#aUakSX;9?iw!5m0!vJfF=w%PNU_ioQ`6`yHZLg_
Sz_uLoyF!O#bQfLEu*v82vRJu#MCi5i;X13@|KtyMrX14NwI<@rhd^`YyncNXo;y^bQT*$ij^!eb&JkoqigS};>@jCtgTtS%@$<M
0@F;rhqKv2tXXK9srhg=TbMPAOfz*K&Ss0SX0d6e_QTn13~QE{X6iqj%@$?N@}`*@5NET+ShIp@rVhl}Y;o4CXqu@7aW)&vnw3m5
^&rk><4Cj6>_N0O^EO+8H8Xn<ZOy#RmSoM$9z<I+Z?mOXGqVTL*38>%Y1Yi_L9{jVHd}@@GkXwi&AiQ)WzEbUL|Zd&v*lPbvj@@E
%-d{v*39fdv^DcKTY)t*dk}5Syv<f5%_6f0(bmk{Y$evr>_N0O^EO+#_Gii^SzEJ2TeCWgtwM?gmY5!6&SI;QVxc9brqNk!HBv0H
#MCo7i>*$I#g>>_MrW}#NU_8cQ^)8m)<BBoEipBW&SK+9v4SP0e$iQMO;W6AiK$(57HcHMN|u<qMQ5>~_MR%q+?plYn$_DZWX%H8
OudJ*S;U%!rkR=#XS0|!i%c_hAI@e8YZjYkYCoLK@~l~6nyLSAHY>1ZdDBb{h_hLdH7l5A>Oh>$N~~GYG*b)WY_=9_Rx-`hgE*V5
O`3&f52CG^x7j+Znc0JAYvygXE^B7?AljOFo2|#1nLUWMX5MD&vu0)wqOF;?*#@kc*@I|n=54kiYi9N!+M0QrZN!?HJ&3ku-ew!K
W@Znft(mvkCajs+gJ^5!ZMG?C7MVSWwr1XDo3UnQ52CG^x7p^kKT|HBwKdCYYgT8mEl9Dz64PVMS!_#EEVRVbG&+lIMT$k1n0iKM
v8_q5*b-CA=q$DkDVA7b>KL8Hwk5^#mY5nwXR+-_v4SP0e$iQMds3`uiK$(57TbXoD_LUd7M;a*ti7koXKu~%+M3ndY$w(%FwN9^
IGgRvnuVsBnh$5QU0AcoG*kECY_=<F7Mo^jKb*~WW6cuNO#O$m+3u`a-ZWDK;%v4DYgRDL)PXpg?a7)IO*6G1&SrbDW+l^1J&3c}
-lSP*_8{7td7JISnwdR_wr1XD`?6+c52CG^x7mKInc0JAYvye>fi*LG5N*x8&Gu)_%pOErGjFpd*39fdv^DcKJAgGadk}5Syv>?f
GqVTL*38>%B5P*$AljOFo0Unk$m~J1HS;!`#G08sh_+_lW|M1wrd%OwYgW+Ktj=OnNU^{Y(__q8tc4T{EipBX&SD3WVv!}Lp3zzC
AW|&0#MCl6i?xzsi6y3v(OImG6w6y;Y8aix+DWm3C8mDSS*(K;D_UY|7oEjANwJb8rf$($?BLpaszT=0te~w~z0E4DSzwx}_i#4r
V$DL+OwEV0SvPAInP%!foXvVzv)D9K`{8Uhl{HIDGxZ<NW{0q5dDBb{h_l(DtXaV{QwQQ~HjOnanr3Q2oXrkn%}S=3dJt!`!%4Hy
>_N0O^ENwzH8Xn<ZOy#Rj%3Zu9z<I+Z?mIVGqVTL*38@NXx7Z^L9{jVHamtjGkXwi&AiQyWzEbUL|Zd&v*TDZvj@@E%-igE*39fd
v^DcKJApMbdk}5Syv<G|%_6f0(bmk{>?GFA>_N0O^ENxV_Gii!v$keMZO!T|b_yvLSYmpNIg6c2iiMV#nnq`_(@3$%5>wCUEOt66
7F%L!8J)$>AjJ|(OdX@M*qNkQ-V#&8=qz>?DORw=)Gs=VolS}rEitu=&SK|~VkJvV-J-MDxwZFH#muc)QCqWmo1Mp+1*VyL4`;LU
S+meIQ}f|$b^&V^nP%!foXsv|&0^C`?T543MXXt3nyLSAHoKTL%bR9uK%C7kVa*DrnK}?>vrAdCqG_fU#M$gJ)~sZjsRwa3yPPx&
%^pNsGjFpiSTnN+(bmk{>`K<m>_N0O^ESJRH8Xn<ZOy#Ru4c{59z<I+Z?kJyGqVTL*38@NTGq_$L9{jVHoJ~BGkXwi&AiR7XU)tW
L|Zd&vm015vj@@E%-ifn(kwE25N*x8&2D1N%pOErGjFq-Yk#I(DQjz1($=ibVz-cDfhDHLn6uceq*!Q)scCc;yNwi!EHU+r&SJNd
VzDKrmeE=44pJ<!#MCi5i`_|z<t;HajLu?rkzxf)O#Py>*xjU9(GpX;=qz>*DOR$?)Ga!T-CKK4Rm$9&m9#ahx7mHHSzwx}_i#45
pEV0jGc_O1W)HAtk!hyx!`bXX)+{#7)P6XdJ;a(NrkVN=XS0V{v%G1h2E^Iy5!S3=nyCYEHhYvcE1G6%L7dGVW6esYnR*asv&TuZ
(Ck69HS;!mf;BUH5N*x8&7Ne<%pOErGjFq}STnN+(bmk{>}l4_>_N0O^EP{iH8Xn<ZOy#Ro@LF<9z<I+Z?orEGqVTL*38@NdDhJA
L9{jVHhY0JGkXwi&AiQCB+VkT2hrBd+w3LQ%<Mt5HS;!mxpuRlarUv<tfyINZB}QqS6H*aG}GhE+3Z!;EHus3H#(cW#+pT@nfgX&
v)5U(*fdk$=xp`|YnGU1>KmQS-ek@4rkVOiXS26hvw~@+zR}t2ZPu)4nyGJeHhYIPE172M8=cMGos-#Ob2?Mcxd_n$tzK&H(Q1LM
rY^);?R{D;wAIvxIIDd?t3|e&`VeQe4{5d7R#PM5to9MDme^|QM4Z(=rq%McnpzQOwNGfZf~}@r#98fATCHfSsTpxr`;1mA*=p)W
oYg*O)k3=)(JIYb?F(AX?nbmr^H%!~t!8&4TBdoceV10VyAf^Eyw$!(tJ&R%)@j~q->22=ZbbVuZ?zxLYIZlGg_^h84{0^K8_`D1
TkS`*n%#|PrRJ^nV_MDbMzmA&R{II77TMj1mTKN=Kc&^|ZbVx(Z?&Hh&#MbEw`zg5YIQdIIcpY}W_p}CoBe_{3r#aMkj`emWX&Se
O#P#?*{@i$*fdl7=xp|D)+{m2)IB<z{f0Hmn`UYroy~sBniWhl^^VSFzhljcrkPqtXS3h4W+l^1oujkaABgrU$lj_2+N#xC?T@rt
V5_MMaaQ{itrps9YD1jW{!FVywwn47XSKi3YO$@RM#Nd|ue4fXtEm%lR{I;RmbcZ^ia4wNomMN@YU)Lt)&4=N6>T*&BhG67q}58c
nz|8ZwSTc{q1}yWtLCltZ(7anMzmG)R{IaFW_Kgns(GvZmsYd85pC7H)xM<F>~2I`HE*@tKvvD}MzmG)RvSR8+1-e?YTjxCX*IhW
(N@h{Z4j+ycO%-Wd8-Yk)$DFWTQzUBA*@<tcO%-Wd8-Yj)$DFWTQzUBVFPP_UR{{ERSUIMtFzf~)+{j1^f+@in};<EO*1u+&Svwn
W|3*8{?XZNKGrNY&D1_Rn~h-264OlGqqEsa)+}$Dsd;oZo1Zl+m}cr7oy`_t&5EX(T1RKIQLI_XG*jp3Y&M!`ufpuDTBxmBz10?^
)dE{hU5K;VLbO_FtEmlfR$G`>i)=OZA<k-x&}y-*rbfhBZ49lJ*lOxToYfYk)$+EQS`lZp#b~vHt)^bYS#5Dzt!S&M8F5w{ORJS^
HFYD-YU5b7(C$XGRr6L`f>yJ;5pC7H)t02y>~2I`HE*@0Xf?YV(N@h{ZE0G~?nbm#^Hy7iR<pYiZPmQhmZjC~ZbVx(Z?)xUHM<+p
R?S;&d0NfxMzmG)R$GBqv%3*()x6bKWYr?O8_`zHTWuv;&F)6DRr6L`nRs4Zl(|)lv{kFK*($7AV4CT1=4`eqYZjVjY9O7>R%6W~
(@g!Nv)SsbS!|lAeRMWkgEdP`Gj)&7W(}-a-ZWG5=xjEgH7l5A>K&cU)@03!rkPqtXR}7utYn(0b96Qfi1sSV-l|2~s?}R9q}2jj
O<jnyT12abwwl@yXSJACi)=OZA<k+EtrpvAYDApX^0ZoFtEm%lRx8kId0S1bh_hOeRx8+Q>P4K@O0-(hR#P+LthN@dR<hO9jX0~V
&8mfVH=?bYx7s?in%#|PtLCk?F0E#FBigEYtF1??+1-e?YTjz=(`t4%qOF>@+6J_m-Hm9g=B>6Nt!8&4+Nyc0ZA7ct-H5ho-fA1u
YIZlGt(v#mCbXK}jcBXpt+pwv7TMj1wrbvLo6%}^H=?bYx7y~!^XlTvty-+DTAj_dV9f&4Oph~Xvn^S(&@@v6>1?(YYZjSi>K~oW
wr0&@(@gE7v)MMRSz?;0dvrG2mNm<pW@;Xt&9-CB3Z|KQM`yF`S+k;Prq<EfYzNk?WSXgSbT-?OXs_bzty-+DTD{eFqSXRhO<jny
+Rn6EXsf9WaaP-fR*P&k^&!q`yV7d0t)@oAS#393EwR<qi8!n6POIf@HMJtnYJ1RX1zSzMh_l+Bv|7<tQ#0bMwim5dvend$IIHc=
s)cqpqOF>@+CH?J-Hm9g=B>6bt!8&4+Nyc0?MJKG-H5ho-f9zQHM<+pR?S;&e_GA%MzmG)R%@cw>~2I`HE*>8Xf?YV(N@h{t(jJ{
yAf^GywxVsYIZlGt(v!5nN^GIZbVx(Z?#FZn%#|PtLCjXnRs4ZlDSn&v{kFK*%a0+FwOKhb2e*X%|g>m4WzT#fvj0%nyG(uHamzl
i%m1NkIrVTtXX23se5!bYh%swrkR>YXR~(JtYDg{cXT%EV9koAnOa9@vrg8mWSXgSbT&JfXs?p&ty-e3TD{dOv|3=RsS9yd>!Q^{
TTN|<vsyQ;7TId*L!8xmXtmf@QzPQ6HkDROY&CTv&T5CyYI$2tt%$SQp|o1TR#PwHtTv5SE81#mMx50Sqt!~bnz|8ZwZmDp(C$XG
Rr6Lmf>yJ;5pC7H)sCdq>~2I`HE*?}Xf?YV(N@h{?Pyxf?nbm#^Hw{CR<pYiZPmQhj-}P?ZbVx(Z?)rSHM<+pR?S=Ocv{WwMzmG)
Ry%=Kv%3*()x6bCWYr?O8_`zHTkRxT&F)6DRr6LmnRs4ZK69&<*H*30W~Z=bfoZ14nX}octXXK9seyDhJB>AqOf&V5&Ss~xX0d6e
_R-nw4Av|$&D1?Qo1Mv;<xMj+kIrUiv1SF+OueJC+1adF(KJ)*=xlZlYgRJN)HynvolCS=`RuJ)UR$+#tDQ%y1-6>H5NEaXX|>Q+
Qyb!}b^)yx*=p)ToYgL*)nZ#sjfk__MYLLCtEm%lR=b#1%iC&dMV!?xq16huntBmuwM%KWqOGQ8#98e!TCHTOsT*-tyPQ=E?QTR{
HE*>mXf?YV(N@h{?MhnB?nbm#^H#fxR<pYiZPmQhuBO%OZbVx(Z?$V^HM<+pR?S=OT3XHSMzmG)R=bW?v%3*()x6cNr`7CkL|Zj)
wHs(PyBpC~&0Fn8RxPr-5pC7H)o!BI>~2I`HE*?>iRaZ7GPi04ZPn^*b_;73m}YvMIh)<enuVsB8c1ie+gP*6G*kcRY<4?q7Mo^j
ADzwaV9gTKOx>fi*`2Ie-ZWG5=xlZuYgRDL)H^zx-OZX6O*6HQ&Sv+pW+l^1oujkay+nIe$lj_Iv{kFO+I_TIV5_MMaaOyZRts%4
wIR-G5726nt)@Q2S?xhuEw<Ivh&Zb~M5`sXnmQ3@wTEf7ysf5I#98eTTCHHKsTXlpdz4ly+G=V>oYfwq)k?OSx)Eo!$62+|?nbm#
^HzI;R<pYiZPmQho}|_6ZbVx(Z?&grHM<+pR?S=OX<E(hMzmG)R(pn4v%3*()x6c7rPb_iL|Zj)wdZIxyBpC~&0FnxTFvf8v{my~
dx2K7yAf^GywzT0)grqa(N@h{?Il{x?nbm#^HzJAcwSvGbE{U=R;|uvudrr;X{N`Sv)QYxS!kN6fpj)|jWvr*Gxd+oX0Nkmv1z9E
(b?<`)+{m2)IB<zy~&#8O*1u*&Sr11W(Ctsy`!_)+pJm9G*j#7Z1xUoRx-`hIXauYOSD(T?5$c+TeW(ty+^ABwwk&SXSMffwa`{m
8{(|?0j(C<YU)Fr)jp)vVp~m(h_l*9v|3`TsS|Nl`<PbC+iGe>oYg*|)e5$ndJ$)}PieKHt)^zgS?x1gtz@gI8*x_qoK*|$ZbVx(
Z?!LIHM<+pR?S=OJG7eJjcBXpt@d47&F)6DRr6N+9<63~BigEYt9_qVv%3*()x6byK&#o^h_-6pYCoja>~2I`HE*>a(Q0-#qOF>@
+K*{9yBpC~&0Fm!tXgDuBigEYtNoN#v%3*()x6byMm(>sl(|(aX{%Oev!AnOfoZ14nX}n1ShLVHQv>O2_Dj|*GR@RKI-C89HH%F%
wU5qbzh=!6(@fo?v)ON0v%G1h=F!>gx2##gG*j>BZ1y|WtZ164b#ylSJ!@7n&D1$MoBe@kuS(flwUV}K^;Y{Mtrpm7>O!2={zR*V
wwl@yXSF}mYLTs`KEzq=FSJ^0tEmxjR{JZhme^|QM4Z+BMyus*HMJtnYJaEI3bvYh5ofi3&}v0nP0fh2+COQvlC7q0#98fMtXgPy
BigEYtNoi+v%3*()x6dIL#x@{h_-6pYX7Cx>~2I`HE*>qX*IhW(N@h{4FaT^-Hm9g=B+k>R<pYiZPmQh2GVMFH=?bYx7r|D&F)6D
Rr6LGOsm=5h_-6pYC~AH$nHk8Rr6LGN~_u3h_-6pYQqNA{JgrbF>9+9HfpO@XS3m~Szwy!apr6`4{H{hW@;dv&E{pzBGXL$qqEt3
tXXWDseN=d8^M|-rkT1&XS0#4S>7~L^XP0gKWkPn&D1+On=Qba6-_g>j?QMIShJF8rq0pXY;^7I)r>RsoQn``)#|0TAgvbIYU)Cq
)fS@FLR(F3h_l+lv|41VsSj~hTZC4NZ8bF_&T3<5wZv9aC*rKOD6N*a)zpeOt1U*W6>K&2BF<`y(`rRqP0fh2+E`kxWUHwgaaJ40
s)cqpqOF>@+7h&y-Hm9g=B>6Qt!8&4+Nyc0Ek&!@-H5ho-fBzJYIZlGt(v#mGPIiAjcBXpt+p(!W_Kgns(Gs|N2}T0h_-6pYRl7V
b~mD}nzz~tw3^+GXshO}wj!$*+1-e?YTjxq(Q0-#qOF>@+RDW9>VnLzTA;03oy}HZ%>vU*k27bpRavvpG*biVY_=L}7MW)1ADzus
XU$^MOzoqy*&3`_Vw$OYbT(^X&GM$1nn!1|@vK?FG*j>BY_=wARy57jIy##*vSuaIOr4{%SwOT`LH1TH&{nP9Y9Xx_*lOxRoYf*)
Ewt6thB&Lmv|41VsSj~hOK7#&R#PM5td^(M5?f83h_hOOR?FLJYDJvYinLn6R#PwHtX87cinf}X5ofivXtk29rf$SpZEaR9w7U^)
)x6c#q1EheL|Zj)wRLGVyBpC~&0B3fTFvf8v{my~Tc1|5yAf^Gywx_K)$DFWTQzUB4QVyI8_`zHTWup+&F)6DRr6Ncm{zm95pC7H
)i$Bk>~2I`HE*>|S+&USMzmG)R@;nLv%3*()x6a<C!SXqW^UC&ZPn^*wgqbzm}YvMIh$?CnuVsB8c1ietyr_jG*kcRY_>IP7Mo^j
ADzv%Va*cLOx>fi*|w}%-ZWG5=xnwfYgRDL)H^zxZO@t&O*6HQ&SpEXW+l^1oujkajzoJEW^dI(ZPn_nwiB%u*lOxRoYi)w)k0fM
ZHTklF0@)?tEmrhR@;?Ui)}SEBF<{N(Q1jUrcT6JZFgENZ>y;laaP-dRx8+Q>P4K@_N3K{wwjs|XSKa(wUVu-Zp2w_Z&od|yAf^G
yw&!h)$DFWTQzUBeQ7nj8_`zHTWvpD&F)6DRr6MxK&#o^h_-6pYWve_b~mD}nzvdLt!8&4+Nyc09YCwu-H5ho-fGRXn%#|PtLCjX
kyf+25pC7H)yk||WOpOls(GtTqSfqfL|Zj)waLWu>Y~i8TBNO7oz14OW`Sv@$C<NP3u_jdW@;dv%?@PEBGXL$qqEsTtXXWDseN=d
Yh}$6(@fo?vsoK!mN(7RJUW}Tvt|X;OueJCSqE!YG|kjHI-7N}W+l^1oujka!9;r%WpC9YZPn_nR-x4bTTNYvvsxFe7TRiRL!8yR
X|>2!Qy=22)<dhswwf9dXSJ!cT4JlI6LD5MgjUPjYHCHC)efcA3bvYh5ofh&v|7<tQ#0bMb{MTzvend$IIA7bs)cqpqOF>@+7Yyx
-Hm9g=B;)lt!8&4+Nyc09Yw3z-H5ho-fBnFYIZlGt(v#mF|?Z9jcBXpt#&M}W_Kgns(Gs&N2}T0h_-6pYRA)Rb~mD}nzz~sw3^+G
XshO}b|R}5+1-e?YTjxm(Q0-#qOF><+5o)ui$P!An#&DD(qE>(w;{+-WEe6WnFpB{nGYF(j6~)~7C=TJqmc!3=_f%hw{R}KBXhYi
$fC$%$l}OYWE`>tvLvz;vNW;`vMjP3vOKZ^vLdn)vNEy?vMRC~vO2N`(twOd)<hbS^lnV=iU>*nlT(;HQb3AG30VtS8(9Zg7g-Nk
AK3ue5ZMUX7}*5b6xj^f9N7Zd64?sb8rcTf7TFHj9@zoe5!ngZ8QBHd71<5h9oYlf6WI&d8`%fh7ugS)fb5SnAqODM$V8-!OiDkw
kSRzDav*XL(u%Yp?MMgGi5!enkS?Sf=|QF<haiU{(~!fE!;vG9Bax$!qmg5fW0B*K<B=1P6OogUlaW)9Q<2k<(~&cfGm*29vypR<
bCL6q^N|aX3z3VEi;+u^OOeZv%aJRPE0L>^tC4GvYmw`a>yaCf8<Crkn~__PTanw4+mSnvJCVDPyODd4dy)H)`;iBb2a$)6hml8+
N0G;n$B`$HCy}R+r;%rnXOZWS=aCnX7m=5cmyuVHSCQ9{*O51nH<7oHw~=>{caisy_mK~f50Q_MkC9K1Pm#}%&(p^o@*U*6$oG)%
BR@cXi2MloG4d1Sr^wHcpCi9Oeu?}F`8Dzz<hRK0kl!PJK>mpQ3HdYf7v!(V-;lo}|3LnU{0sRv@*m{C$d@x7`~#4I$RK1eG6Wfl
3`2$^^C0sg^C2UUk;weW0>~(2G_oMF5VA0`2r>p)6j=;e92tv@LzY06M3zF9MwUUAMV3RBM^->qL{>spMpi*qMOH&rN7g_ZknzZx
2)?fMelZIXe8tPfNP^^%0#Zau$XdwS$U4Zn$a={7$Og!U$VSM<$R^09$Y#jq$QH<!$X3YK$TrBf$acu~$PUPk$WF-4$S%mP$Zp8)
$R5a^$X>|a$Uexv$bQHKWPhXyIRI%!CL(2I5;7T?g0vt9A_pO@NE_0QbReC`!AJ$^Lb{P2WGZq9awswlISe@*IRZHnISM%%IR-fv
ISx4<IRQBlISDx#IR!ZtISn}-IRiNpISV-(IR`lxIS)A>xd6Ekxd^!!xdgcsxeU1+xdOQoxeB=&xdyowxemD=xdFKmxe2)$xdpiu
xed7;xdXWqxeK`)xd*uyxevJ?c>sA3c?fwJc?5YBc?@|Rc>;M7c?x+Nc?NkFc@B9Vc>#G5c?o$Lc?EeDc@23Tc>{S9c?)?Pc?WqH
c@KFX`2hJ4`3U(K`2_hC`3(6S`2zV4@?GS6$oG*SAU{NYg!~x!3G!3qXUNZyUm(9keuexR`3>@0<afyLkv|}RME->Q8TkwHSLAQV
-;sYH|3v<U{2TcX@?Yf38GrB(Kn5a%kip0hWGFHW8IH_@%!|y2j6g;r^CJr&qma?ag2+P1!pI`X7-UgoF=TOMEHVyR0$CDS3RxOi
23Zza4p|;q0a+1Q30WCg1z8nY4Otyo18G3UBWof!0Oas3S}sH)Bt{Y>j}#Cb#&bB@<<>&hM%F>rMb<;sM>aq<L^eV;Mm9k<MK(h=
N47w=M7Bb<Mz%q=MYcn>M|MDVM0P@UMs`7VMRr4WNA^JWMD{}VM)pDWMfO7`Ap0Xt$N@+*G7%{wlaR^C6r=??5IG2GMcR;dqyy<h
4n`_S7t)RNAXAY;kVBDa$YIFg$Pvhq$Wh4A$T7&V$Z^Q=$O*`a$Vte_$SKIF$Z5#w$Qj6)$XUqQ$T`Tl$a%>5$OXuS$VJG-$R)_7
$Ysdo$Q8(y$W_SI$Ti5d$aTo|$PLJi$W6%2$SugN$Zg2&$Q{U?$X&?Y$UVrt$bHED$OFiO$V14($Ro(3$YaRk$P>tu$WzGE$TP^Z
$aBc^$P37e$V<q}$ScUJ$ZN>!$Q#I;$Xm$U$UDfp$a~29$Op)W$VbS>$S26B$Y;ps$QQ_WknbYjL%xsv0Qn*EBjm@(PmrG?KSO?w
`~vwU@+;)m$ZwF}BELg^kNg4oBl0KY&&XepzaoD_{*L?u`6u!(<lo4DkpCiI&iJN(05T96gbYT8AVZO1$Z%vHWL{)GWCSu2nIBmI
8HJ2S7EBL;$im1X$QWc%WHDrMWGpfcSpr!SSqfPiSq51aSq@nqSpiuQSqWJgSp``YSq)hoSp#W6#v^MYjYxomNQA^lg5;3`QbbC~
TFBbSI>@@nddT|72FQlUM##p<CP@0@-P0cyp8n|R^hX(|KN>gvQLE{X?o59aWcs58(;ror{^+yxM`@)$nkoH3Kk1K+Nq-1Q`XepU
ACQo~+<yAv?deN_r!Op>zD#lYqPOWwsHQK-nZCSZ`eK3UOV6b*WR|`xR{A1K=}Y#cF94IioJjie6zR(yr1SZ7j-AeX)46CmKTPLr
={zc(+oa=-bPA9@u{?d6a{8p#^eL3-6Y|ohcco7jN}qa?K9M24ES_FuO)uG{7l6{s328Z<R-I{amew%oq5fp#6y#LoG~{&T4CGAY
EaYtD9OPW&Jmh@j0^~yEBIIJ^668|kGURgP3gk-UD&%V98su8!I^=rf2INNMCgf)17UWjsHsp5X4&+YcF63_H9^_u+KIDGn0pvmC
A>?7?5#&+iG30UN3FJxSDdcJ78RS{yIplfd1>{BKCFEt~735XqHRN^V4dhMaE#z(F9pqi)J>-4l1LQ;GBjjV`6Xa9mGvxC@)6dtl
oyOzo=lJQT_4Q^J3O$p?PYuS$<GY&LI$O&VCrnMtk@AG5_K6c_b`}#lTguJlLt47Z6Ixr^%S{!0$cP!I?0TN+TXnMkf9_;IaJJL^
sD3!%kLrh0{t|QHq(5X1r~TnIocIT4ocaf6ocssQcKS~rjA{VX0H^^_1E2;#4S*T|H2`V=)Bvaf`2VK?h-RMhJ1ZR%dwQS6Fuu8`
QfX=K!6|=2`s{-V2X?fycTbr8`3cjDgUn|l1pf!6dc+X
"""
_NEED_COMPRESSED_BASE85 = b"""
c-rmV1$12X8ZGdt7ighH3bat%Ny(8h+}+*FG@Z7A7?Y$>+}+*X-QC^Y?Yg`B<?WMdxTo{Ye&n0-
*4ua8y=XH@Wqz47|9xgBTWq`aE<11181~OBmzmsMYAH2zRN5zYH+40)w>3;GH?@>1<%tcYwo+Gn>$FVI|GpY9{lA$-
GEJq*#D=NOop{5B&hE;jQd4=s=`XCbAJW*+)ZWtAKQkbMpY+Q#4$k1`-K}l-
;h0RN+|}Hcyj4fJsjGq?G*>F6iOr?9rgD&(R4GmW1GG<?{b!i@7M1d(a;1#do8wK!X3B@+O&Yq}n!6f0+q)~cwNh>=PfczdH#Nv)
7Rz)tPj166)AK5&Nt2q}$_-
P4{+WiLU*>=RA7=6Q>$yM1wKPvHkHg;|{~6y|ZtHBXOdGfP`0~NHv2%PdzN4kPbA0Fc_NnE{_z=I<K)fOThWJ%x+)Fcl_CNoRjoZ
U&w?|dq9xtj*CrHx?q~oj8zeb%fO(&F&ug-uPb)qz#NIJec18dZY({y6#`05O*Q74<Gla-FI&fpq#a%nm_>G<jlsZl4NrjwVBug=
gKbqZ-Z1?l+e%xCKay-
%ZoPNQ|xnZHJzAWcW7QD>b6YSanSbaWbZ))`i#PL!sj)2Oq~@EUdEG##BroplzhQ74<GqtmFf&O$Zn<kEC>8g<qgQKL>iO-
H9uXPuEX>J-v+bQ*QmS=iPId!I%_okr`Xvq+6PL7I+Eqs}^u)~FMv>F6}-
tg~2+I#HUAPNU8`qiWQN({ywib=FzDMxAV$j!vV_I!n~3lS|XlY1CO~$r^R?X*xQMI_r$CQKyimqtmFf&X~FBEH>kgZ|M2^fAa~u
gEKuZo^=&_=Fi3D%e5586;$WadDWR~X^tzb&ZPsaGuK#-
E2_?=6Rk7XG8|W2ol8etXRc*Au55KKoq3(PmgBf`)wy&CcIH~1<H}d((y7>)YXy$0P@PN1WM{4wIj&-
LuA;bnxmKDR*QoSk^4w~TAv4a&>NT9fRwls$15C|^GuSF5SZIK$+i(V3l?00nFtr=bV5^Z}u>q!j!x?OK5-
e+gso`)2TZ0748DQ!-
oWa&4!SV)}S`KHhhMJGfLCV$TKv$RR%QcSU3aWGI4Cc(W7RMD<=h6wxnX8fGimG$z{N>CQa9nY9E}g!dxk8RBTb)a1FK4cZ<H}X%
(#gx2E9SWJ)wy);a^}i%T!rdfy1MMlmE*XI)wy(a*_kU}a}5=wU0n`zb-B)91rjVUz|?FwgB3}z&;V1n;S9Dm2^JY(YB!w0)*-
=S15EvfGuXN$Sk?ej!{H3J9toB+z|?U#gRM`3<qa^k9L``H)O>6XQ?4$Dy1HCnt_?Y^pgNb%V9s0{aa>__E}g)fxi;pwqUu~ae>r
n)!g0mbxpew+=Gv6w%2wyn*~^)0Gma})ol7S#XRggTu6%Vaox7a5w&1u5)wy(a*_mrgj;mOmOIMejxwfjgh6>ZJE{D3hTxYPYNwB
~GQ?ua=whaju8er-
+oWZsw!6E}p?S?bhb|hGAfT`bb2HTzl%Nk&6IGn+DAi;75m^uz;upLRTyaA?`!x?O+nvcy<%GKpaSC{L{wKK;RROiwe%$aK!jw`I
rr4yJl*RC8_RGmxbFK4dZIIg%lmrh^KT)T5z+3H+6dpUFM!ExoPbLr&e%(W-
Sm9NgFbC)yMUL04UI+w04J9F*LaTTj`>FTmG*FH7ZP*K{|<w#eT>kPIp2^JV&YBrp~_9MYU15Dk9GuZwlSY&{y-
EamQPlCk;nEDN8umec2tO2Hm!x^kZg5?Y_bsWxM6G*VU0j8G28LX-
1V{@Exbvf46<@$0><hX+BTsng}bCo%+usWAcV9s2VIIgHVm(E|#T$4GjxH^|kU(Q@pIIe7UE}gxcxtckyTy-
v;yqviX<hb(HxpeMw<~oSuDpcpv)n#X{7LKb}ol94jow-_TuA$<ztIM&jF4q~XjRXq}Ff|*_VC^JWXn?8Pa0crj!6E}p?S?bh!6a
C0fT`bb2CI-
@Sp!TBhcj3w36?X!)Nwe2b&+6s157Q4Ggx=c$L4Ix)#a?NF4vc9D#sO6=h7L>nd=aaE3D3?6PPpCp&VCKolEC0XRc`+S6rP-
r!Qx&!#J*NbuOK~oVgC?xN_CGbn<fMI)dZMSLf2X%bDv)j;m0eOIMejxsKwviq*Mvb=jHg=$dP&Y}(c3tgbHC8SEGmEHJ>-
Y&e4*OM-<4n7R#Tu;WOu$N*Ej;S6>>2^Je*>NlLhP9VXu2ACQSXRs4Vu$%#=j>8%3BoZudfT`v11?!i*c(F`-
Wpb&lxwEyQT&gs5RLY%DD-
X&fKf_xLNPd8~9h+%uue6q0nhz^a9N#fzT4!@psbzfm(5B|DQi8C^oVQN^L1kJl)*asa_I}nK9?ZJK1Kr_$aEJGw`yD<KA8neZw3
JH?jSUk@Z4(<B8wbpKZy!GM#!Am^c*&SdQ@O3HQf`=3!Cx64Sf(|!Hn+4iPbpWr4jYsyG~$1wdcW1I-
>NbFL)ENTp8c_E=3B_I_w551$DoR1P}Om8Cdfv`I4?*q$bk%GSOqdPAj3GDYYYVG1v!X;jH*CJ24s{ihWgOz2RWF5jH^J#24uET|
3-R34q+g(RUoqlWG)|PgHVuOkV6^BTouTi0a++E76Sbn=>|C;1DUS^nXd{tBohQ#Sn6Y|o8<hAWTA>=!IF%NK~RvSo8$tFWU-
25(UL4SMvY-
4NiWG^gk&)HZl`}HXf!CpIEdoBS^+o8;S6O^jWRGOqsBNFWOJhQqFj)n469Lw7G)u7jKWxyUX%+llu<Rx$e@f1jbWJ0iqea61Vb5
Dql^v8Tw`Od*r*S%Zj>V#%4{{ttU;MqW9Lh`a4nR<|6H96banE(<+upr7*ui8)ya7axhMk}R)N&j$$1O87y}tqfz;K>c?&s;fsCs
_>gwdYg<PD0%vOQa)ya7axda25s{*O3lk*mGNd_`s1yWZh=dt8yMzT;vQdcMEvE&#=vRFk@S10GO<WhuWF!ydpS10E^<<bmgP>oV
oC+9KcScWpJMyacl^O$lOhBB%~sjHLom~vT$GOk9ctCRDXayf=FTa8jzC+96?GM&tfnoZf%-qw}eJ)Kj^<*vkX`cEtEhcwRlrKj-
=&D?S0hofe_UT1SxxuLzOsk;Mr=d_jQrZdMY<0U1T^fu{7nFMJjflT_=q(5a6rkR8?>06Tllu49k63L`*O$JgXahgdilfE?>M44p
MOtLcRTa&?*NiNMKCzHN48A6%l(@gR*>06Vblu04Yq#%>NHJPtglc4vRG0>UO&18PcBuF#SnX!*e7NAVRG!vZ}``Ba{WfG;C=*-
y1Cc`O{IL$<7#y&P#kTS`pndr>e$0iF=Cb={dof-SsWCUfBPczY(v5!qgQYM8o6P+3R*ks{aO~T%1#!zQQH<LvulOWARXU0A@S(G
vf(@b<`>|>L~D3d77L}$i6HW@{k#AzlvGxo8`;*?1?%|vI$J~ml`GRdWx=*-y1CQDK#`7{%q8T;5|G-
XmqGtrr`k4>iU<fi|j8#+oYt)<G$J8f8IO1Wj$UD!V}EHj~f;<TCHifC|V`fCrH1yVY+xwH4%2&+%AlIP-OmY)3pYHtBV7yjT4<&
Neq-0{ubtt(f*xuMiDu{>qk#B%@4h)mOza%=Lva2lGXl-k<LEkiRiZ(X$Kw)RT7soc@?o>3{aO)eY1^|G1SFP+-
ng1fe*oS61J`Ml>l?KGsjcb2-klUHb)-22tV-<!Xm&A)=dU+(NGSJLbUWqNKB{C5$)zYV{V0T0`ba$D-den@7<jl%yf;t%-
tkNQ$;b2|N?OwUb%|1QE0{PvIf&hD0uDczOyNBxW&h5uc|A7taNXyA8DDYvz^q}k(h_nzBC|6QaX{Ouq2Ey;`K_OJbn8-
@Q}#2;egFK_*8-
_$%YO@3e|xkc>XLH6X&kQqJOU~+e7SE=XTp3$}}TjjQf&O^%OuJljudTvT5ulCz5lbQXZnXQbt`;NPx!M#jX?ovxv`r|vfMcCgp?
Ec>hyFLBWcVM^A?Q?fw&pYe^2KI8*uqQNk&840joSA-
`z`twY1Ha9`+}*9E*5>qoxqEIB_jimtIhJSU_<%jJxw8Z3sd6jsu!iYO?Ul~anO-
l)UD?*zGX35^G`Wt}+1`quHT7IE8=mQP^YB?Wf~mE<c&0qLy+;EtnNXgDcLm(V_&_jv`o*|jzt2qAxm;fB^}3xMCE0$%w%@n3omS
m;nr!EtZU1j+dsubb!(=<}YzNe0yJT<MN_*FgM`h`dZ_*CS%z3M1=bdcwhgd#Ss^H%5Zkhf`P0yX&T24MsYM+I>^z7G3?&C_iv!l
5({q-lcv;%l#?_VT&hRKM`H(%`=(hJUhmuhLp=VoJiy}{Jv8A-V7%ebw%Yg&*l-0OFp{-
^HwG*8(7i#@1D?6JMEaYs+XC&jo^C%3eBbv1XUYLCqP&+8f7OMde$@Za{1avMHH7WTKs9$X{#=-
$}v72Kbtj&cR3m2xWd@Jz4QF_0JT{n|axI+O0V)*bSHrwfJV9*@q0n%m~0+v{}<-Lbu2yGIwG_&2+?=Qot}x0X)6cF-DgKBqT%5V
cKgXzK1NwUyhuI~%&Dlq;>X$;V{6%B^52^*r8Yzgp*%a!b#}>YjI$ruNnjFeINCEtL7jD~-
<d{E`5f{iSD{+wd9K)Kbe*nJ^zUHa0eNwKqgz&yRY()a^m#mZ{BcGv0F6AEsfBKT0nBeWBVfr+0{ycZm7ecZd<a-
yzy7<+S&LftlnM(SL{OGbiK4i)5Ngm5B{gn>)LckC@X-$x-
;sxvROY)G#UesQf=)>3B$H`paj1J+WCY7&GGylaIaSrmo}zd2^*wn%JD&!*luQJ@YN*cn_KNCKBr{b_yvLSYm<1e8o;B#X?Igl$f
vBX{1<WiA56g6+4|2i!HHOV!mQ$kYZU&EGsczu`@}roF$f%n6KDbq*&e(%S+5x>}*o3V2KqZ<|}p%DOR+^iW2h`J9lnki_hf*J=f
A>=*%OuS`TNl^H{UMG*j>4Y<50t7Mf;iKAg=iV9g@aOx=gG*@diGY?`V4a5lS$HOrc2>OY*#E@sVgrkNTLXR}LKv%G1h4#e5)Qr4
_snyCeGHoJ^9E1G8NL7dGlC(S~$2MN`KIGbI;nwdRFs2;@G>`K<m>_I~HAkJo2v1Vou5~>GrHoKZNGkcIwJ&3c}HLRK0gM{iqoXx
If&CDJoR1e~8b{%VG_8_5p5NEUNSu?W-3Dtu*o87>gnLS9T9>m$~M$#-Ydyq&yh_l&EteM$^MCw7D&2Fy!nQ}qe)-
2H0tj=P$kYa%)rpK7G*sY{kXo;z5bQZgf6pJh|^^DG9x07PAC8n0qS?mr{ENh9WV{{g~lN8HYVrm$j#qJ`-
@|KwTMQ5?QNwI<@rgqU;>>g6AXo;y?bQZg}_MR$8-
I@j3n$_FvKGrNS&D481o88Zvg{GOB4`;InShL79Q}^L)_8@B(n`UZ1oXs9$&9bJM`VVKbhgq|nX{H9m+3XS4EN_~r193Kclr<}uW
@<s4%^qXTil&)*5NET;Nwd)GL9{jVHhY3KGkXwi&AiQ?WX;STL|Zd&v!_@yvj@@E%-
if~*39fdv^DcKdxkYLdk}5Syv?3v&CDJ|TQhI7=U6kd2hrBd+w6JP%<Mt5HS;!mfi*LG5N*x8&0ZwUBC`k4*38@NCDzRBL9{jVHh
a1DXUc_XTeDDGvpS2tLW%{Jm>y%!Vy}{7p(UoK(OK*@QY^B>)H6DZy-
te7mY7;bXR$X(v8*Mgj?r1{O;RjpiK$_97JG{n%UfdV7oEl4CdCStnA$~Wv3E$Zq9vwo(OK->+Iy-nb!!%CYgTWw_gJ&QG*j>4Z1
z5D7Mf;iKAg=yV9g@aOx=gG*@vuIY?`V4a5nphHOrc2>OY*#K4#5wrkNTLXR}XOv%G1h4#e5)Q`W3tnyCeGHv5b<E1G8NL7dG#C(
S~$2hrBd+w2S0%<Mt5HS;$6k~K4X5N*x8&AwvI%pOErGjFr+v1VouqOF;?+4os9vj@@E%-ie-teM$^Xlv$e_Cwap>_N0O^EUetYi
9N!+M0Qr{g^c~dk}5Syv=?>nnh+0qOF;?*-u$Bvj@@E%-
if|wLeoXO52)6+M3l_?B}FdV2SB5<}CILQY^H@)HFJa{gM=mEHU+r&SJkJ#bQfLEu*v8uSv12C8mziS?o8YSk4kt!{{vbTT(1<iK
$<77W*A3R<Oj>E;@_-o)jxuV(J#1#r{xxPZgzZ%_42h>TUK%)+{j1)O$Fa{fRXTO*1tg&SrmR%_7rG-
G{T;Us$u)G*kQGZ1z{yENhyn|8O?@8*7#`&D4N6oBf?N%bRBEK%C9~!I~9JGqoVjX8&Z(il&)*5NET0k!GRUgJ^5!ZT4^0%<Mt5H
S;$64{K)jAljOFoBfwHGkXwi&AiRNX3fkVL|Zd&GrWv5GkXwi&AiR}v1VouqOF;?S%22d>_N0O^EMm6nwdR_wr1XD16eb(2hrBd+
iVbN7MVSWwr1XDgIP1P2hrBd+iXa`nx82br)|w*ZO!T|Hk1?#EHORCoW<rN#X?I=O{25e{G?c9iK%CF7F&Q6i!Cv=jLu@iNU^LXr
jF5BY&a>Fv&7UeI*Tnxisdaa^^4A83z1?4OHA#ev)BkytZ0d;TXYs1S$j_vr*6$+ZO!U!wlHfJm}crdoXr+t%|g>m&4;tuqO4hDn
yLG6Hd~A}i%m1NAI@f@ShK8YrvAg(Y;o2sXPT)2aW-
3mHOrf3>Oh>$mSoKerkPq0XS30)S<y6858`Y#hBOP!9z<I+Z?mOXGqVTL*38>%Y1Yi_L9{jVHXF;DnLUWMX5MDYux4ftqOF;?*|M
ye*@I|n=54kdYi9N!+M0QrEzg>nJ&3ku-exPXW@Znft(mvkimaL0gJ^5!ZMG6=7MVSWwr1XDE3;;152CG^x7jMSKT|H7wl&LYYgT
8mRY|eH64PVMS!^{@EVRVbG&+l|PKrgAn0iKMu{B7s*b-CA=q$D-
DVDXw)G<1XHIQOCOH2);v)DLNEN_XaUvw5*ixewZVrmzi#TrSmq9vwo(OE30y{F2iZq2gVn$_DZWX%H8OudJ*S;U%!rkR=#XS0|!
i%c_hAI@f3)+{#7)P6Xd<yf<<X{P?e*(}eR<xDd*AkJn5)+}$DsRMB~E3#$<(@ZUhv)S6LS<y6858`aL4rvyeJ&3ku-
e&8vW@Znft(mvkdaRk*gJ^5!ZMHsZX7(W3nt7XTz?zvoh_+_lW*f3*W)GsRnYY<SteM$^Xlv$ewlQmF_8{7td7Ev*nwdR_wr1XDo
3dtR52CG^x7lW-S!DJg+M0QrZO)pRJ&3ku-ez0W{!F=C+SV+mty!JLwj{*@OH7Y3XR)nFvCtAz)95U=H7OQZV(J;4#kL{EVoOXdq
qEqyq*&GxQ^)8mwjC*!v&7UeI*V;jisdaa^^4A8JCI@pOHA#ev)GQLSkV$wx9BXkQ|&!fE_G{`)7GrsW;?THfoZ1R!`W;X)+{v5)
O<Lb?aG=(rkT1AXS3Z{v)D9K`{8W1J8PCT&D4K5o9)4x<xDd*AkJocvSxYHOdW``*<P$!!8B6~;%v4zYgRPP)Pp#i?L(S{W)GsRn
YY=#teM$^Xlv$ewjXO|_8{7td7JIenwdR_wr1XD<5@Ga2hrBd+w1_=%<Mt5HS;zrv1VouqOF;?*#y?i>_N0O^EPW@&CDJ|TQhI7i
L9B~gJ^5!ZB{1DBC`k4*38>%5^HAmAljOFn@z6$nR5BGtyx}MvpS1SA;khqOph^Vv1U>%w8YdjI*T1hiba-
~dPZllgGjO15>w0QEY?DbWi2svjLu@Mq*%@pQ^V*i)<%luEiv_r&SLGPSiurgyXY*|L5dYEF?Ea1Vh7jWQ{_{)W_fMR>TOnG%>vU
*y@#_|Cu<g(W@<j1&AM2#$TU;;;cV8;n#HD>+7D;5sjOMnG*kcKY<381mNU)NfH<2S%9`a(Gj$-
&X46=+f@!7}#M$gH)~slnsRwa3JDfBN%^pNsGjFpaSTnN+(bmk{>`2zk>_N0O^ENw*H8Xn<ZOy#Rj%Llw9z<I+Z?j`qGqVTL*38@
NSk}z!L9{jVHam_rGkXwi&AiQyXU)tWL|Zd&vlCb|vj@@E%-
ifl(kwE25N*x8%}!#?%pOErGjFq#Yk#I(A#H0`(AKQZVyBQ|fhDHLn6ucaq*!Q)scCc;JB<{JEHU+r&SIyNVzDKrmeE=43{os>iK
%0B7CVy^%UNP-
7@ft=BE|BSnEFL$v9n3Bf+ePQ(OK*qQmkl+satdwJGb_ps*t)hD`;z0Z?p4Qv%oY{@8N8AK5G`5W@<j1%`RZgBGXLWhqKv*tXXWD
sr_&^yNET*nr7-
hoXsv~&2pxh8W3l*OIWkKX{HXu+3Zr*tYDg{1#vdJj5RBoX6iwl%`PX+LbC_a*38@N3f9c*L9{jVHoKBFGkXwi&AiR7V$IARL|Zd
&v#VJ%vj@@E%-if5*39fdv^DcKyOuRGdk}5Syv?p-
&CDJ|TQhI7>sd3i2hrBd+w2C`%<Mt5HS;#Rku;0U9z<I+Z?l_NGqVTL*38@N=GvbrS4`WQ6}2_1v)C=9SYV0iG3G3GD=8LQVrm+l
#cm_TB1=p?qqErUq*!c;sbzE)yMq+VT4L%LoyG1X#d4OI8b)WayGXITC8mDSS?q37tYC?$U33<^hZHMXV(J#1#qO=Wrz)my&5GKZ
)!Xbo)+{j1)O$Fa-OrkZrkR=#XR`-
bv&b}4_u*{zAZr$zW@<m2%^qUSvZk5(4`;K7S+ksJrUt~>>=D*1Z<?tCaW;FDH7l5AYC)XM9%IdlrkQ#WXS2siv(W58v^DcKdxAA
Hdk}5Syv?3u&CDJ|TQhI7r&u$y2hrBd+w5u9%<Mt5HS;!mhBY&L5N*x8&7Nh=%pOErGjFr!STnN+(bmk{?0MGA>_N0O^EP{dH8Xn
<ZOy#RUL?&Tvj@@E%-ifG*39fdv^DcKd%1SApmENz+3crTX>C?#vsYNNz%<k2%-QT!)+{v5)Hgbty~dhFrkVOiXS3H?v)D9K-
{@@i25Xiz&D1wKo4v`J<xDg6jm~Cov1WPGOnsxX+1spH!8B9f=xp{5YgRPP)Hgbty*oFvCFXXfo_i6Z1zNq--lNq5TTNYvv)cQ#T
4<}O4RKccfL4oaHT5CRY9G>Sv8|>?#98elS}kj<sS|Nl`<PbC*=lM<oYg*|)$+EQdJ$)}PieJ+t)^zgS?x1gt!S&M8*x_qoK*|$Z
bYjzZ?!LIHM<+pF3nr*OIpqDMzl=xR{M%pv%3*()4bKbN2}T0h}LP|YTu{T>~2K+G;g&Z&}w!!qJ^5b+7D?pyBpC)&0Fn9w3^+GX
r<<@_G4Pj?nbmz^H%!_s}|Yah?Z*JYComb>~2I`HE*?_5zng&QnzY>wrX`Y`#EbCm}YvMIh*~0H49BMHIU9`zhuoK(@g!Nv)Qj$v
)D9K`{-=;Yt}4lnyGtqHv0{0mNU)NJUW~GmNm<pX6hZC&3?z46-
+a=j?QMkXU&SHnL0;jvp*2+Rgk__3$#_Mx7r_RwZK+W7vik;Ct5AE)zpSKtNoc)i)=OZA<k-
lq19qrO^t}N+Fxn4tgWU_#98fcv|7$qQ!C=E_IFw>Z>y;naaQ{WtyZwr)QmW*{gYNJ+G^@XoYnrts)cqpqOF>@+P`TvyBpC~&0Fn
1w3^+GXshO}_Fr1f?nbm#^H%$sR<pYiZPmQhGW}UKyBpC~&0DP>t!8&4+Nyc0^{3VBZbVx(Z?yrmn%#|PtLCjXkXEz15pC7H)dsO
@k=>1GtLCjXm{zm95pC7H)rR!1{dsj^>Q*h(R;|uvLs_%HG}GhE*=#=6EHus3KsuYv&zeQ1nfga(vjteQ*fdl7=xjEOHOrc2>K>i
VhO=fl(@f2yv)O{IS>7~L@91o{5NlR2&D1(Nn~h-
2il&)5M`yE<M0*vcZ`DF=)#|ObFs&BYYU)Cq)fS=ELR(F3h_l+Fv|41VsSj~hTZ~qVZ8bF_&T6A*wXChCPQ+Plaat{BtEm-
nR$GEr%iC(|MV!@^q}2+xnwk-3wb8U%(N<G8;;c4?RSWHIL|Zj)wWVk^yBpC~&0B40TFvf8v{my~8%wL%-H5ho-fGLxYIZlGt(v#
mvb37rjcBXpt+pJkW_Kgns(Gs|PpjG8h_-6pYAeucb~mD}nz!1Dw3^+GXshO}wi2rr+1-
e?YTjxq(`t4%qOF>@+A75J>Y~)GTBNO7oy}Hd%>vU*k27bp)mXF8G*biVY_>XU7MW)1ADzwCV9jFFOzoqy*_y0b)-+T1=xo-
&n&nJ0HIL3_<5;u2X{O%M*=#M=tYDg{b#yjsWX+1EnL0;jvw&!?qV%m=q^(-
L)k0b=u+`LsIIBgpT4<}O4RKbBX|>2!Qy=22mZjBVTTP9Kvs#W;%i3z{M4Z*~v|7$qQ!C=ER-
o1LwwihoXSE`&R<PC7j5w>UO{*1cHFYD-YU{9Sq1}yWtLCk?F0E#FBigEYtF1??+1-e?YTjz=(`t4%qOF>@+6J_m-
Hm9g=B>6Nt!8&4+Nyc0ZA7ct-H5ho-fA1uYIZlGt(v#mCbXK}jcBXpt+pwxW_Kgns(Gtz#;QejH=?bYx7y~kn%#|PtLCk?1@XMPI
CZNQYpYggvn^S(z%<k2%-L)!)+{v5)Id6$ZOxiRrkVOjXR~csv)D9K`{-
=8Eo+uF&D1?Qn{CIM<xDd*kIrV>vu1hIOueJC*$%8(!8B9r=xnwlYgRPP)Hynv?L@R!ar#y*)>f_FYCF?vfvu)4#93_@S}nBI)P^
{#?Mkafwwn47XSLmEwb)iuBjT*KJFS+r)zpbNtL;In<!m*zBF<`i(rS5IO}&V-
+FrC;!B$f<;;gnetyZ+v)Qvc+?Zc{tb~mD}nz!1%w3^+GXshO}wjZr#cO%-
Wd8_SDtJ&R%wrbvL<7qX!8_`zHTkQZ^&F)6DRr6LW(Q0-
#qOF>@+5}q7?nbm#^Hyu3)$DFWTQzUBiL{#CjcBXptyX5$BD)*WR?S;&60K%;BigEYt4$`JSC>uQs%5oRtFze@)+{j1^f+@iYi7+
t(@YJdv)O^HS!9~2e{?oGh&78%GqsP-W-Y8))-+T1=xo-?n&nJ0HIL3_ZLC?|G*j>BY}U@26-+a=j?QKstXa`CQ|IVxb}-
RiWz)B6S#8zotyZDc0$WX8h_hNJtrps9YD1jWx@fh?R#PA1tkzAd#kQIn5ofijv|83yQzzoAb_lJOv(?m!IIA5>tL1Gq^&-
w{(`dDVt)^zgS?w@dt!S&M8*x@UoK*|$ZbVx(Z?z+6HM<+pR?S=ONLtPAMzmG)Ry&GTv%3*()x6b?rq%3jL|Zj)wPR>CyBpC~&0F
nQTFvf8v{my~JC0VfyAf^Gyw#4U)$DFWTQzUB6KFNN8_`zHTkS+vEwZ~2ZPmQhPNLQ9ZbVx(Z?%(&=hfv>w`w_U)#_|^3TqaaW_p
}Co1My<g{GMrNN2OtShL79Q~&5}b~<Yon`UYsoz2c*&9bJMx<_ZTGg-
5oX{P4U+3YOVEN_~rcXT#8n>8z#W@;Us&CX%Xil&)5M`yEhiS{a&zE#U<t5$Ed^JuleR#O+^tad)F7TRiRL!8wvpw%K<O?`;7+J&
@QY^$jeaaOyCR?FII>O`E?E~eFTwwhWIXSGXcwY;sSUc_1LQd+HGtEm}rR=bQ=E81%6Mx50yXVpTx8_`zHTkQ&3&F)6DRr6N6l2)
_35pC7H)vlt|>~2I`HE*@6X*IhW(N@h{?HXFm?nbm#^H#f-
R<pYiZPmQhuA|lLZbVx(Z?)@bHM<+pR?S=O23pPTMzmG)R=bf^i|lShTQzUBn`kw=8_`zHTkU4zd3E{Jty*4NwK|*K!kPu9nI31(
X1B6tp=qWD(%I}b)+{p3)IU0#-
OifDrkUDDXR|w4v#e>R?$O!oPSz}EnyGnoHoJ>8%bRBE9i7eYX3YwwnOa9@vwK*xqG_hi(b?=?qP@zeZ`JbJs?}TVK3XlX)zpPJt
KCnlg|?d75NEXqXtl^zQy=22_8_em+iGe=oYfwp)v~slIuU2JhiSE(t)^DQS?v*8EpMx-
7jag5lvXR)YHCKD)gGhOinf}%5ofi>S+&saMzmG)R(pb0v%3*()x6c7q}A+hL|Zj)wWnw`yBpC~&0FnhTFvf8v{my~dxloCyAf^G
yw#qi)$DFWTQzUB=V&#%8_`zHTkUyT&F)6DRr6MRfmXA-
5pC7H)m~)PBD)*WR?S=OC0fnyMzmG)R(qLvUR@z|t5(oft<Gkzux5d2rpKAH*{iHsXqu^kbT)g9HH%C$^^eYGud`;cX{Pqk+3XG0
ENhyndvrE?lQqkkW@;Xt&E8_o@}`-3M`yFQS+jy^rq<Ef>>bvuXqu^WbT)gJXs-
(CTeX6=YV}rok5&t8HFY7*YVXr(p{=Gi#98eFS}n5G)Q32$eMqatwwf9dXSI)LwXChCPQ+R5V_Gd|tEm-nR{Mlj%iC(|MV!?>rPT
_ynwk-
3wa;j^qOGQG#98fgRxPx<5pC7H)xMzB>~2I`HE*>qX*IhW(N@h{?JHW%?nbm#^H%#Ft!8&4+Nyc0eV<mdyAf^Gyw!d{tJ&R%wrbv
LKcv;{ZbVx(Z?zxMYIZlGt(v#mk7+f#8_`zHTkR*TT4Z-4+Nyc0{ghU-yAf^Gyw!e2Jg=^px>YM`t5#>TpR;CxX{N`Sv)M0Lv(Pk
C1L<t`OV%th&D1|SoBfJ4i%m1NkIrVlX3esunYu@3v){00InzwdqqEs>S+l%prry!n?02kL!8B9r=xp|T)~slnsdIET`vcKl71Ot
BMQzpUt@cM+EwI(pg*dDIiB=13HMJqmYJaBHB3n&;h_l*XXtmf@QzPQ6_E%ahYpbafaaQ{qt(LRZ)QUK({he0J+iL1XoYnq8s}*c
DH6zYy|D@H5wwk&TXSIK^YN6eYXshO}_HSCv?nbm#^H%#0t!8&4+Nyc0{g+m=yAf^Gyw$#@)$DFWTQzSr2#{)aH=?bYw^~11&F)6
DRr6NsPpjG8h_-
6pY6ECByBpC~&0B3Ct!8&4+Nyc04Pw<IyBpC~&0B3St!8&4+Nyc04H;1L^XkIJw5?j$sI6L^&4#jOfoZ14nX}n^tXXK9seyDho1Z
m{Of&V5&Snd+X0d6e_R-mF7;Ba_&D1?Qn+<2pa;BM@M`yDIS+l%prry!nY$4XHV4A6QbT%8oniWkmb&k$vBWrK3W}K<#UW90?Rxh
=MX|=#sQy1c_wg{~j+G=V;oYfYk)goI>eTcK#VzgRptEmxjRvSgDWo<QeBF<`y(`q?eO|6Kt+7h%{-
d0mD;;gnLtyZwr)QmW*ji%L#wwk&TXSFe`T4;A8+Nyc0Ek&!@-H5ho-fBzJYIZlGt(v#mSX#~QMzmG)R$GQvv%3*()x6b~rPb_iL
|Zj)wdH6vyBpC~&0B4GTFvf8v{my~TY*-
yyAf^Gywz5u)$DFWTQzUBl~}dN?nbm#^Hy7#R<pYiZPmQhRw15O7o=|00&UgmY_=+E7MNywoH?7V#+rqunHorEv(;I%$TU;`=xnw
IYZjYkY9F1=)@04HrkT1&XR`*@EN7ajd2}`#$C~9$Gxd(nW^1u#1=CEeqqA8fYgRPP)Hynv1w?xlq;J&%ZPn_n7Sd{gt)?!-
SuLW~LR(F3h_hNut3|e&`VeQeEUgyXYHCEB)pE32)>cy|;;fdZ)pE9)S`lZp0<D&})zphPs}*Urf~}@z#93`^TCHfSsT*-
tTZdH(?QTR{HE*?bX*IhW(N@h{Z9Q7e?nbm#^Hy7*R<pYiZPmQhHlWq)ZbVx(Z?z3+HM<+pR?S;&BU;VwMzmG)R@<0Xv%3*()x6a
<q1EheL|Zj)wM}U?yBpC~&0B3VRxPr-
5pC7H)i$Tq>~2I`HE*>oi09RXsav&BTeUiyZONJirkNgR&SqP&W}#`O2GZGVYt}3>&D1|Sn{C6I#ip6sM`yEbS+lHZrtZ<%Y&+I0
XPT*bbT-
?bHOrf3>K&cUc3{m4rkPqtXR{qyv!ZFH&e7RyC!)Oy)3<7&wrcfO+nH7iY&CTu&T6~RYN4&BHpE$NS6VHy)zpVLtL;Xs#kQIn5of
jCX|=4arcT6JZ4X*4XRE0daaP-tR?FLJ>P4K@_M+7awwjs|XSKa)wW6)2Zp2w_A66~2yAf^Gyw&!l)$DFWTQzUB{b)728_`zHTWx
<@&F)6DRr6LGPpjG8h_-6pY6sA2b~mD}nzvesR<pYiZPmQhCeUhjH=?bYw^|deW_Kgns(GtTq}A+hL|Zj)wKA&~+1-e?YTjy-Xf?
YV(N@h{Z8Gt^x+rz47HO+iXR|4+Szwy!apr8+%$kL!nHorEvjbVP$TU;`=xlZnYZjYkY9F1=T3EBJX{PSc*{qc{%b8|s9-
YnFShKuorry!nterJ0m}Y7noy|H}v!ZFH&e7TIV4}T>(zj}nwrcfOtI%qJt)?!-S*?>+3vD&EA<k-
Dv|41VsSj~h>!#IWTTP9Kv)WWzEo-
Z(6LD5MgjUPhYHCHC)efcA^0u0K5ofh&v|7PdQ#0bMb{MTzwAIv&IIA7bs)cqpqOF>@+7Yyx-
Hm9g=B;)lt!8&4+Nyc09Yw3z-H5ho-fBnFYIZlGt(v#mF|?Z9jcBXpt#&M}W_Kgns(Gs&N2}T0h_-
6pYRA)Rb~mD}nzz~sw3^+GXshO}b|R}5+1-e?YTjxm(Q0-
#qOF><+MpNk;$<`KmC2>H=FZlJ)^b;ALVHVdQ$urGSGm&ORPN|%uXK*h%)X(m+;bOqmMc@sxX&jwH#K+l&y2`SXrDL@tgRiTN>^*
St!vrLAye90$_=xA?Mk^R`MXb>`No|KXXX$}e!HoqmK8IN4PEUGK|`u+Q>mkb-
)`DMnQ#07R+`&;!t~c_E#X&hF11L%xBiPY>5uuQe%F+8r4<jbmiE%bH2P(}Nk8)qzP<dg%$&cu*#B?X`{AWu4VZarCet5DewzH*1
|fryA;?f<K4gAm0c03599a-
q2pNHlL>A5@ANezxMKj4AnaPYo7DtvqmPAG)W00kgrIE47GCl8knapy?^2iFvipWaH%E&6ns>o`{>c|?%nn(jO4p|FnM3TEPxho<
h`70+dIV6u1kRq}+vJSE?vL3QNvH`LovJtW|vI(*&vKg{DvIVjwvK6v5vJJ8=vK_KLvIDXsvJ<j1vJ0{+vKz8HvInv!vKO*9vJbK
^vLCWPG9EbqDIpV(CS)Q~MkXciT*wrp895L+2x&oDkv60q=|B!fDo7{Ng>)lRkwcI}k!i?b$l=Hl$dSlV$kE6#$g#+A$nnSt$ce~
F$jQhl$f?L_$mz%#$eGAl$l1s_$hpXQ$oa?x$c4y7$i>Jd$fd|-$mPft$d$-d$koU-$hF9I$o0q#$c@NN$j!(t$gRk2$nD4-
$eqYt$lb_2$i2vY$o<Fz$b-
m3$iv7Z$fL+($m7Tp$dkxZ$kWI($g{|E$n!|@Z(;Hg@g?MC<Q3#q<Td1V<PGFa<SpcF<Q?Q)<UQnl<OAeG<Rj!`<P+pm<TK=R<O}
4><gtf*5BWaw1LTLukB}cDKS6$q{0#Xy@(bjb$ghxJBfmj@i~J7xJ@N<SkI0{pKO=uZ{)+q!`8)Ct<e$jDkbfipLH>(;J>$XO59y
B#Kn5a%kip0hWGFHpGC#5aG7K4xEQl<Gj6g;r3nPmliz165qmadsC6FbN(a0ENDP(D6EV2x;EV3N3JhB3^BC-
;)GO`M?DzX}~I<f|`Cenb6L)Jp@ajoZrS%}~xUM5DeNDj#(1*C|qjjV&Li>!yNk8FT!h-
`#xjBJ8zifo2#j%<N!iEM>zjckK#i)@E%kL-
Z#i0p*yjO>E!itL8$j_iT#iR^{!jqHQ$i|mK&kBmnSKuX92qzRdbl#xluWMm4`j2ws@gtQ>7NE_0QbRY*K6{HjCLb{Qu$RWs~$TZ
|I<Z$E&<VfTw<Y?p=<XGf5<ap!+<V55o<YeR&<W%G|<aFc=<V@r&<ZR>|<Xq%D<b31;<U-
^k<YMF!<Wl4^<Z|Q+<Vxf!<Z9#^<XYr9<a*==<VNHs<Ywd+<W}T1<aXo^<WA%+<Zk31<X+@H<bLD<<U!;i<YD9y<Wb}?<Z<K)<Vo
Zy<Z0v?<XPl7<ay);<VEBq<YnX)<W=M~<aOi?<W1x)<Za{~<Xz-
F<bC7=<U`~m<YVL$<WuA`<a6W;<V)l$<a@~XkslyGM1F+)82JhEQ{-pJ&yimszeIk8{2KWU@>}G0$nTLqAb&*ug!~!#3-
VXwZ^++~e<1%v{)PM-
`4946<m(y#@b^RdBLk3u$RK1eG6Wfl%!ka6EPxC{h9e6i3n3$rk;uZxBFLi1V#p|DabyW(Nn|uK23ZPO8X1c$gDi_Ihb)h*fUJnD
gshCLf~<<HhOCaPfvkx%Amfm=5S;om_!KP@A`ucJStN(#kpfag)<)Jr)<xDs)<-
r#Hbgc;Hbyo<Hbpi=Hb=HVwnVl<wnnx=wner>wnuhAc0_hUc1CtVc13nWc1QL=_C)qV_D1$W_C@wX_D9Ae2OuS60@8%wbLmVOnS@
M6rXbD8fyhBf3(|_TA?-
*9axhXsIuRVhGTq2j<PhXgWEyf9ayW7XawKvTax`)bax8Kjay)VZaw2jPax!uXaw>8fayoJbawc*XayD`faxQWnaz1haav^dNaxr
oVaw&2dayfDZawT#Vay4=daxHQlay@bbawBpRax-!Zaw~EhayxPdawl>ZayN1haxZcpazF9_@*wgM@-XrU@+k5c@;LGY@+9&U@-
*@c@+|Tk@;vea@*?sQ@-p%Y@+$Hg@;dSc@+R^Y@;34g@-Ffo@;>qb@*(mO@-gxW@+tBe@;UMa@+I;W@;&7H$PbVoB0oZYjQj-oDe
^Pq=g2RRUn0LkevSMF`7QE0<oC!QkUt`SLjH{W1^FxTH{|cgKahVS|3dza{0I3j^7V{Q`uidMkpaj+WDqhK8G;N&=0oO37C?p}!;
uA%g^&@*NMzxp`9T&%7DGlMiz7=QOCqC@G00NL(#Tk38Dv>xIb?Zc1!P5JC1hn}6=YRpHDq;U4P;HE0U3v^g)|}o5+V^2BUvPe<d
FhWMAk;uLDogqL)J$&KsH1+LN-
P=K{iD;LpDc}?>C=(|MKMfVJF{TIr)CQ$@hOvzMp9F{V9|0cbI(tyyW|_CEwjE`Cd`UcOFW<k4^GjQIhYmk$lI7<m>+@Urj#w+T_
Vsx=y}sa`IJpldtKTe1*{D>rEzKy)gM&c*$2*OTJE5@>QRbuOXCtO`7CuoFrc}Bl#K($)-Qqh$oxlWW$<lB9o0>ve-
)YKgpUT*(M~<bWff)ojeOSc}{2Y48i32X34XclIOxC&#XwU(<fJblWT~{6{+O<M$(oi-D}e1os67<oQj-
=oQ|A<oQa%;oQ<4=oQs@?oR3_9T!>tRT#Q_TT#8(VT#j6UT!~zTT#a0VT#H<XT#wv<+=$$S+>G3U+=|?W+>YFV+=<+U+>P9W+>6|
Y+>bnfJcvAmJd8YoJc>MqJdQkpJc&GoJdHeqJc~SsJdeD9yokJnyo|hpyo$VrypFtqyotPpyp6nryo<btypMc<e29F6e2jd8e2RR
Ae2#p9d^uqHIeU&%c|83*KmF9c{;Xo5d(yb6!MJ!_XQ{QLr95%`)T9|Lk1w@N96zhO7~j!cZYm$r+*uyq(%e=qRq!UmXPma{dAe`
W3IG4O6Mp|WPWdDH;G{pI4^I0_&4UyFpt+p-ht_cNADD9bADGer^q-
>zNFI!80@MVk2~ZQDCO}PqngBHcY68>*s0sN0rwK?Nax>e2Xx53pqtZUHyXV;q<C?lFmFA{yocPBl&qx@5V0&|0*Z4V~voO6xNPT
uf@P7dJg3)~
"""


def receptor_anatomy(*, include_focal: bool = True, include_need: bool = False) -> object:
    """Restore the exact roster declared by this input's spatial coverage."""

    if not isinstance(include_focal, bool) or not isinstance(include_need, bool):
        raise TypeError("receptor spatial coverage must be explicit")
    if include_need and not include_focal:
        raise ValueError("metabolic need anatomy is appended after the focal field")
    # Canonical positional cache key: default and explicit True share one Arc.
    return _receptor_anatomy(include_focal, include_need)


@lru_cache(maxsize=3)
def _receptor_anatomy(include_focal: bool, include_need: bool = False) -> object:
    encoded, expected_bytes, expected_sha, port_count = (
        (_NEED_COMPRESSED_BASE85, NEED_ANATOMY_BYTES, NEED_ANATOMY_SHA256, NEED_PORT_COUNT)
        if include_need else
        (_FOCAL_COMPRESSED_BASE85, ANATOMY_BYTES, ANATOMY_SHA256, PORT_COUNT)
        if include_focal else
        (_COMPRESSED_BASE85, LEGACY_ANATOMY_BYTES, LEGACY_ANATOMY_SHA256, LEGACY_PORT_COUNT)
    )
    raw = zlib.decompress(base64.b85decode(b"".join(encoded.split())))
    if len(raw) != expected_bytes or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise RuntimeError("Guala receptor anatomy asset changed")
    episode = guala_core.settle_native_joint_source_episode(
        raw, port_count, port_count * OCCURRENCE_FRAME_COUNT,
        OCCURRENCE_COUNT, OCCURRENCE_FRAME_COUNT,
    )
    if (
        episode.schema != ANATOMY_SCHEMA
        or episode.port_count != port_count
        or episode.source_sample_count != port_count * OCCURRENCE_FRAME_COUNT
        or episode.occurrence_count != OCCURRENCE_COUNT
        or episode.occurrence_frame_count != OCCURRENCE_FRAME_COUNT
        or episode.python_callback_count != 0
        or bytes(episode.as_bytes()) != raw
    ):
        raise RuntimeError("native core changed Guala receptor anatomy custody")
    return episode
