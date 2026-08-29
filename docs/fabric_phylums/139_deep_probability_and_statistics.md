# 139 DEEP PROBABILITY AND STATISTICS — reasoning under uncertainty
Probability is a small set of rules with enormous consequences.
Statistics is the harder half: taking numbers that came from somewhere
and deciding what, if anything, they are entitled to say. Most of the
mistakes live in the second half, and most of them are about the coming
from somewhere.

ESSENCE: probability rests on three rules and nothing else. No chance is
  below nothing; the chance of something happening is one; and for
  outcomes that cannot both occur, the chances add. Every theorem in the
  subject is squeezed out of those three.
ROOT: premise — chance is a way of sharing out one whole unit of belief or
  of frequency across the possibilities, with none lost or created.
THREAD: money (shares of a whole that must total one), physics
  (probabilities in the quantum books obeying these same three), law (a
  set of exclusive verdicts).
ASKED-AS: probability rules basics add up to one cannot exceed chance total axioms

ESSENCE: the fastest route to "at least one" is almost always to compute
  none and take it from one. The chance of at least one six in four rolls
  is hopeless to add up directly and trivial once you ask about no sixes
  at all.
ROOT: this file / the three rules — something and its opposite share the
  whole unit between them, so either one is the other subtracted.
THREAD: engineering (system reliability computed as one minus the chance
  everything fails), medicine (the chance of no adverse event across many
  patients), computing (the chance a batch of jobs all succeed).
ASKED-AS: at least one probability opposite complement one minus none easier chance any

ESSENCE: adding the chances of two events that can both happen counts the
  overlap twice. The repair is to add them and take the overlap off once —
  and with three events the corrections themselves need correcting,
  alternately adding and subtracting.
ROOT: mathematics / counting — the same double-counting that ruins a
  headcount of two overlapping clubs.
THREAD: money (customers counted in two campaigns), public health (people
  with either of two conditions), computing (the size of a union of two
  sets).
ASKED-AS: probability of a or b add overlap subtract both counted twice union

ESSENCE: mutually exclusive and independent are near opposites, and they
  are constantly confused. Exclusive means if one happens the other cannot
  — which is the strongest possible dependence. Independent means one
  happening tells you nothing about the other.
ROOT: this file / independence is about information, while exclusivity is
  about compatibility — two different questions entirely.
THREAD: law (two charges that cannot both be true against two unrelated
  charges), medicine (competing diagnoses against coincident ones), sport
  (winning and losing the same match against winning two different ones).
ASKED-AS: mutually exclusive independent difference confused both happen unrelated cannot together

ESSENCE: independence is not something the arithmetic can check. It is
  DEFINED by the multiplication working, so multiplying is not evidence of
  it — it is the claim being made. And the claim is about the world, where
  things are linked far more often than anyone assumes.
ROOT: mathematics / chances multiply only where events do not touch — so
  the multiplication is the assertion, not the proof.
THREAD: engineering (two backups sharing one power feed), money (assets
  that move together in exactly the crisis they were meant to hedge),
  public health (siblings' outcomes sharing a household).
ASKED-AS: independent events multiply assumption check really unrelated linked backups correlated assume

ESSENCE: a conditional probability moves you into a smaller room. Given
  that something is true, the possibilities that contradict it are gone,
  and the remaining ones are rescaled so they still total one. Nothing
  changed in the world; the accounting changed.
ROOT: this file / the total is always one — so restricting the
  possibilities requires dividing by how much of the whole survived.
THREAD: medicine (a risk quoted for people already known to have a
  finding), law (the odds given the evidence admitted), insurance (a rate
  for a class rather than the population).
ASKED-AS: conditional probability given that already know narrows down given information updated

ESSENCE: the chance of A given B and the chance of B given A are different
  numbers, often wildly. Almost everyone with the disease tests positive;
  almost nobody who tests positive has the disease. Both sentences can be
  true at once, and the confusion between them has convicted people.
ROOT: this file / conditioning rescales by how big the given room is — and
  the two rooms are different sizes.
THREAD: law (the chance of the evidence if innocent against the chance of
  innocence given the evidence), medicine (test performance against test
  meaning), security (the chance an attacker matches against the chance a
  match is an attacker).
ASKED-AS: probability given reversed backwards prosecutor fallacy test positive disease direction confused

ESSENCE: Bayes is not really a formula; it is a discipline. Start with
  what you believed before, weigh the new evidence by how much more likely
  it is under one story than the other, and finish with an updated belief.
  Evidence multiplies belief; it does not replace it.
ROOT: this file / conditional probability — the formula is only the
  bookkeeping of moving between the two directions.
THREAD: medicine (a test result read against how likely the disease was
  before), law (evidence weighed against the other facts of the case),
  navigation (a fix combined with the dead-reckoned position).
ASKED-AS: bayes theorem update belief prior evidence posterior how think about revise

ESSENCE: the base-rate trap dissolves when you stop using percentages and
  start using people. Out of ten thousand, one has it and the test finds
  them; ninety-nine healthy people also test positive. Now the answer is
  visible without any formula: about one in a hundred.
ROOT: this file / the two directions differ by the sizes of the pools —
  and counting actual people makes the pool sizes impossible to overlook.
THREAD: medicine (screening a healthy population), security (an alarm on
  rare events swamped by false ones), law (a database match in a large
  population).
RULE: to read a test result honestly — imagine a definite crowd, say ten
  thousand; work out how many of them have the condition; of those, how
  many the test catches; of the rest, how many it wrongly flags; then the
  chance a flagged person really has it is the first count divided by the
  two counts added together.
ASKED-AS: false positive rate how many people out of ten thousand natural frequencies

ESSENCE: odds are the natural currency of evidence. Written as odds, an
  update is a single multiplication — old odds times how much more likely
  the evidence was under one story than the other. The awkwardness of
  probabilities is entirely a notation problem.
ROOT: this file / Bayes as updating — the division by the total evidence
  cancels when the two stories are compared as a ratio.
THREAD: gambling (where odds were the native language first), medicine
  (likelihood ratios reported for tests), law (the weight of one piece of
  evidence stated as a multiplier).
ASKED-AS: odds versus probability likelihood ratio multiply evidence update two to one convert

ESSENCE: when a choice is made at each of several steps, the number of
  whole routes is the choices multiplied. Four shirts and three trousers
  make twelve outfits — and this one rule is the foundation under every
  counting formula there is.
ROOT: mathematics / multiplying is counting by copies — each earlier
  choice carries a full set of later ones along with it.
THREAD: computing (the size of a password space), manufacturing (product
  variants from a list of options), cooking (combinations from a set
  menu).
ASKED-AS: how many combinations choices multiply outfits menu password possibilities counting principle total

ESSENCE: a permutation is an arrangement, where order counts. Filling
  three places from ten people gives ten times nine times eight, because
  each place taken removes an option from the next. Gold, silver and
  bronze are not the same as three medals.
ROOT: this file / choices multiply — with the pool shrinking by one at
  each step because nobody stands twice.
THREAD: sport (podium finishes), computing (the number of orderings a
  sorting algorithm must distinguish), music (the orderings of a set of
  notes).
ASKED-AS: permutation arrangement order matters how many ways line up positions first second

ESSENCE: a combination is a selection, where order does not count. Take
  the arrangement count and divide by the number of ways the chosen group
  could have been ordered — because every group was counted once for each
  of its orderings.
ROOT: this file / a permutation counts arrangements — so the selection
  count is the arrangement count with the internal orderings divided out.
THREAD: card games (a hand is a selection, not an arrangement), medicine
  (choosing a treatment group), computing (subsets of a set of features).
RULE: to count selections — ask whether swapping two chosen items gives a
  different outcome; if it does, count arrangements by multiplying the
  falling choices; if it does not, do that and then divide by the number
  of ways the chosen group could be ordered among itself.
ASKED-AS: combination choose order does not matter lottery hand divide by arrangements formula

ESSENCE: the binomial situation is a fixed number of tries, two outcomes
  each time, the same chance every time, and no try affecting another.
  When all four hold, everything about the count of successes is known
  exactly.
ROOT: this file / choices multiply and selections are counted — a
  particular sequence has a computable chance, and the number of such
  sequences is a combination.
THREAD: manufacturing (defects in a fixed batch), medicine (responders out
  of a fixed group), polling (a fixed sample with a fixed underlying
  proportion).
ASKED-AS: binomial fixed number trials two outcomes same chance independent conditions when applies

ESSENCE: expectation adds, always. The expected total of several things is
  the sum of their expected values even when they are entangled,
  dependent, or impossible to describe jointly. It is the one property
  that never asks for independence.
ROOT: this file / an expected value is a weighted sum — and sums may be
  regrouped freely regardless of what the terms know about each other.
THREAD: money (expected total cost across linked risks), computing
  (average work of an algorithm, summed over dependent steps), the living
  world (expected total offspring across linked lifetimes).
ASKED-AS: expected value adds sum linearity even dependent average total combine why always

ESSENCE: the average of a function is not the function of the average.
  Average the square of a wobbling quantity and you get more than the
  square of its average — the gap is exactly the variance, and it is why
  volatility costs money and why plans built on averages disappoint.
ROOT: premise — a curve bends, so scattering a value around its centre
  moves the outcome toward whichever side the curve rises on.
THREAD: money (a portfolio's growth against its average return),
  engineering (fatigue driven by peaks, not by average load), planning (a
  project whose duration is set by the slowest of many tasks).
ASKED-AS: average of squares versus square of average flaw of averages plans nonlinear

ESSENCE: variance measures spread by averaging the squared distances from
  the centre. Squaring is what makes distances above and below both count,
  and the price is that the answer is in the wrong units — which is why
  its square root, the standard deviation, is what gets reported.
ROOT: mathematics / absolute value keeps distance and discards sign, and
  squaring does the same job while staying smooth enough to work with.
THREAD: engineering (tolerance stated as a spread), money (volatility as a
  standard deviation), manufacturing (process control charts drawn in
  these units).
ASKED-AS: variance standard deviation difference spread squared units why square root measure

ESSENCE: variances add for independent things; standard deviations do not.
  Two independent errors of three and four combine to five, not seven —
  they partly cancel. This is why averaging many measurements helps, and
  why it helps only as the square root.
ROOT: this file / variance is a squared distance — and squared quantities
  add along a right angle exactly as the right triangle law says.
THREAD: engineering (tolerance stacking in an assembly), money (why
  diversification reduces risk and by how much), surveying (accumulating
  errors along a traverse).
RULE: to combine independent errors — square each one; add the squares
  together; take the square root of that total. If you cannot establish
  that they are independent, this understates the result: the true answer
  lies between it and the plain sum, so use the plain sum when the errors
  might move together.
ASKED-AS: errors combine add in quadrature variances standard deviations root sum squares independent

ESSENCE: a distribution is the whole story — which values occur and how
  often. A mean and a spread are a summary of it, and summaries are
  photographs: useful, and silent about everything they cropped.
ROOT: premise — a summary is a projection, and a projection discards by
  construction.
THREAD: money (a risk figure that hides the shape of the losses), public
  health (an average exposure concealing a poisoned few), engineering (a
  mean load that never caused the failure).
ASKED-AS: distribution shape histogram mean standard deviation summary hides picture look at data

ESSENCE: most real distributions lean. When a few very large values sit
  far to one side, the mean is dragged toward them while most of the data
  is not — and it is the far tail, not the centre, that decides how much
  trouble the thing can cause.
ROOT: this file / a summary discards shape — and skew is the first thing
  it discards.
THREAD: money (incomes, insurance losses, market falls), the living world
  (seed dispersal distances), engineering (component lifetimes with early
  failures).
ASKED-AS: skewed distribution long tail income average misleading extreme values rare large risk

ESSENCE: some quantities have tails heavy enough that averaging never
  settles. Add more observations and the mean keeps jumping, because the
  next observation can outweigh everything so far. For these, the law of
  large numbers simply does not apply.
ROOT: this file / an average converges when the spread is finite — and for
  a heavy enough tail it is not.
THREAD: money (market crashes, where the largest few days dominate every
  average), the living world (wealth and city sizes), computing (network
  traffic and file sizes).
ASKED-AS: heavy tails average never settles more data does not help extreme dominate

ESSENCE: the bell curve appears wherever a quantity is the sum of many
  small independent contributions, none of them dominant. That is why
  heights, measurement errors and totals of many small effects all end up
  with the same shape from entirely unrelated causes.
ROOT: this file / adding independent things adds their variances — and
  repeated adding washes out the shape of the individual pieces.
THREAD: the body (height and blood pressure), engineering (measurement
  error in an instrument), money (the log of a price rather than the
  price).
ASKED-AS: normal distribution bell curve why so common everywhere heights errors sum small

ESSENCE: the central limit theorem says the AVERAGE of many draws is bell
  shaped whatever shape the draws came from. The original could be a coin
  flip or a wildly lopsided cost; average enough of them and the average's
  own scatter is the familiar bell.
ROOT: this file / adding independent contributions produces the bell — and
  an average is a sum divided by a count.
THREAD: polling (why a sample proportion has a known scatter), quality
  control (batch averages behaving predictably where units do not),
  physics (the smoothness of any bulk measurement).
ASKED-AS: central limit theorem sample means normal whatever original shape averages not individuals

ESSENCE: the long run settles the RATIO and not the COUNT. Flip a coin a
  million times and the proportion of heads closes on a half — while the
  raw gap between heads and tails typically grows, wandering off without
  bound. Both are true at once.
ROOT: this file / the scatter of an average shrinks as the square root of
  the count, while the scatter of a total grows as the square root of it.
THREAD: gambling (a losing streak that never has to be repaid), money (a
  strategy whose average return converges while the running total drifts),
  physics (a random walk that returns to the start rarely).
ASKED-AS: law of large numbers evens out ratio versus count gap grows never repaid

ESSENCE: any figure computed from a sample is itself a random quantity,
  with its own distribution, its own centre and its own spread. The whole
  of inference is the study of that second distribution rather than the
  data.
ROOT: this file / a sample is a draw — so anything computed from it
  inherits the randomness of the draw.
THREAD: polling (the spread of results across repeated polls), medicine
  (the variation between trials of the same treatment), manufacturing
  (batch-to-batch variation in a measured average).
ASKED-AS: sampling distribution statistic varies sample to sample would have got different

ESSENCE: the standard error is how much a sample estimate wobbles, and it
  shrinks as the square root of the sample size. Four times the data buys
  twice the precision — an expensive exchange rate that governs the cost
  of every study ever designed.
ROOT: this file / variances add for independent draws — so an average of n
  draws has a variance divided by n, and its spread divided by the root of
  n.
THREAD: polling (why a sample of a thousand and one of four thousand
  differ by only half), medicine (trial size and cost), engineering
  (averaging repeated measurements to reduce noise).
ASKED-AS: standard error square root sample size four times data twice precision bias

ESSENCE: how large a sample must be depends on how variable the thing is
  and how precise an answer is wanted — and almost not at all on how big
  the population is. A thousand people describe a city and a nation about
  equally well.
ROOT: this file / the standard error depends on the sample size and the
  spread, with the population size entering only when the sample is a
  large fraction of it.
THREAD: polling (national samples of about a thousand), quality control (a
  fixed sample from any size of batch), medicine (trial size set by effect
  size and variability).
ASKED-AS: sample size how many needed population big country poll thousand percentage enough

ESSENCE: a confidence interval is a statement about the PROCEDURE, not
  about the particular interval in front of you. Ninety-five percent of
  intervals built this way cover the truth. This one either does or does
  not, and nothing in the method says which.
ROOT: this file / a sample statistic has a distribution — the interval is
  built so that it captures the target in a stated share of possible
  samples.
THREAD: engineering (a calibration guarantee about a method rather than a
  reading), law (a procedure's reliability against a verdict's truth),
  weather (a forecasting system's track record against tomorrow).
ASKED-AS: confidence interval means ninety five percent chance contains true value misinterpretation procedure

ESSENCE: an interval's WIDTH carries more information than whether it
  happens to contain zero. A narrow interval around a tiny effect settles
  a question; a vast one containing zero settles nothing and is routinely
  reported as evidence of no effect.
ROOT: this file / an interval reports both an estimate and a precision —
  and the precision is the part that says whether the study could have
  found anything.
THREAD: medicine (an inconclusive trial reported as a negative one),
  engineering (a measurement whose uncertainty exceeds the effect sought),
  law (evidence too weak to support either conclusion).
ASKED-AS: confidence interval width wide includes zero no effect inconclusive precision means

ESSENCE: a hypothesis test is proof by contradiction with the certainty
  removed. Assume nothing is going on; work out how surprising the data
  would be under that assumption; if it is surprising enough, doubt the
  assumption. That is the entire logic.
ROOT: mathematics / contradiction refutes a premise — softened here, so
  that improbability under the premise stands in for impossibility.
THREAD: law (a case built by excluding an alternative account), medicine
  (a diagnosis by ruling out), engineering (a fault located by testing a
  hypothesis about it).
ASKED-AS: hypothesis test null logic assume no effect surprising reject reasoning how works

ESSENCE: the test can reject and can never accept. Failing to find
  evidence against the assumption leaves you exactly where you started —
  which is why "no significant difference" means the study did not find
  one, and never that there is none.
ROOT: this file / the logic is contradiction — and failing to reach a
  contradiction confirms nothing about the premise.
THREAD: law (not guilty against innocent), medicine (a test that failed to
  find disease against one that ruled it out), science (absence of
  evidence and its conditions).
ASKED-AS: not significant means no difference proved null accept fail to reject absence

ESSENCE: a p-value is computed ASSUMING nothing is going on. So it cannot
  possibly report how likely that assumption is — it is an output of the
  assumption, not a judgement on it. Nearly every misreading of the
  subject is this one confusion.
ROOT: this file / the two conditional directions are different numbers —
  and a p-value is squarely in the direction nobody wants.
THREAD: law (the chance of the evidence given innocence against the chance
  of innocence), medicine (test performance against test meaning), news
  (every headline that has ever restated this wrongly).
ASKED-AS: p value what it means not chance fluke hypothesis true misinterpretation definition

ESSENCE: power is the chance a study would notice an effect of a stated
  size if one were really there. It is decided before any data arrives, by
  the sample size and the effect sought — and a study without it is asking
  a question it cannot answer.
ROOT: this file / the standard error sets how large a difference is
  distinguishable from noise — so the sample size decides what is
  detectable.
THREAD: engineering (an instrument's detection limit fixed before the
  experiment), medicine (a trial sized for a clinically meaningful
  effect), law (an investigation with no chance of finding the evidence).
ASKED-AS: statistical power sample size detect effect underpowered study before design chance

ESSENCE: in an underpowered study, the only results that reach
  significance are the ones luck exaggerated. So the published effect is
  systematically larger than the truth — and the smaller the study, the
  worse the inflation.
ROOT: this file / an estimate scatters around the truth, and a
  significance filter admits only the upper tail of that scatter.
THREAD: money (backtested strategies selected for having worked), sport (a
  scouted performance that will not repeat), medicine (early dramatic
  findings shrinking as bigger trials arrive).
ASKED-AS: small studies exaggerate effect size winner curse significant results inflated shrink replication

ESSENCE: test twenty independent questions at the usual threshold and
  there is about a sixty percent chance at least one passes by luck alone.
  The arithmetic is one minus the chance every one of them fails to pass —
  and it climbs fast.
ROOT: this file / at least one is one minus none — with the number of
  chances being the number of questions asked.
THREAD: medicine (a trial measuring many outcomes), money (a rule found by
  searching thousands of candidates), computing (an alerting system with
  many rules generating constant false alarms).
ASKED-AS: multiple comparisons twenty tests one significant by chance correction bonferroni fishing

ESSENCE: the count of tests is usually invisible. Every choice about which
  cases to exclude, which grouping to use, which outcome to feature is a
  fork in the road, and the analysis reported is one path among hundreds
  that were available.
ROOT: this file / the arithmetic of many chances — with the chances now
  being analysis decisions rather than declared tests.
THREAD: law (evidence selected after the fact to fit a theory), money (a
  strategy refined against the same history it is tested on), science (the
  reason pre-registration was invented).
ASKED-AS: researcher degrees of freedom garden forking paths analysis choices preregistration fishing after

ESSENCE: significance answers whether an effect is distinguishable from
  noise. Nobody wanted to know that. The question was how big it is, and
  the answer to that is an estimate with an interval — which is a
  different sentence, and the one worth reporting.
ROOT: this file / a test statistic mixes the size of the effect with the
  size of the study, so the verdict alone cannot separate them.
THREAD: medicine (clinically meaningful against statistically detectable),
  engineering (a measurable difference too small to matter), money (an
  edge real but smaller than the costs of trading it).
ASKED-AS: effect size versus significance how big matters practical importance estimate interval report

ESSENCE: a correlation coefficient measures how well a STRAIGHT line
  describes the agreement between two quantities, on a scale from minus
  one to one. It is blind to everything else — a perfect arch scores
  nothing at all.
ROOT: this file / covariance measured in units of the two spreads, so the
  units cancel and only the pattern remains.
THREAD: medicine (a dose-response that rises then falls), money (a
  relationship that reverses above a threshold), engineering (a response
  linear only within a range).
ASKED-AS: correlation coefficient r what measures straight line curved zero strength not slope

ESSENCE: wildly different datasets can share the same mean, spread and
  correlation to several decimals — one a straight line, one a curve, one
  a blob with a single outlier dragging everything. The summaries agree
  and the stories do not.
ROOT: this file / a summary is a projection, and many different objects
  cast the same one.
THREAD: medicine (a trend driven by a handful of patients), engineering (a
  fit hiding a systematic pattern in what is left over), money (a
  correlation created entirely by one crisis week).
ASKED-AS: same statistics different data plot it anscombe outlier look at scatter first

ESSENCE: noise in the measurement drags a correlation toward nothing.
  Measure either quantity sloppily and the link looks weaker than it is —
  so a weak correlation may mean a weak relationship or a blunt
  instrument, and the number cannot say which.
ROOT: this file / independent errors add variance — the extra scatter
  enters the bottom of the correlation and shrinks it.
THREAD: psychology (constructs measured by questionnaire), medicine (a
  single blood reading standing for a long-run level), economics (survey
  income against actual income).
ASKED-AS: measurement error weakens correlation attenuation unreliable instrument looks weaker true relationship

ESSENCE: regression draws the line that makes the total squared leftovers
  as small as possible. Squares are chosen because they punish large
  misses hard and because they make the arithmetic solvable — which also
  means one wild point can drag the whole line.
ROOT: this file / variance is a squared distance — the same choice, made
  for the same reasons and with the same cost.
THREAD: engineering (a calibration line fitted to readings), money (a
  relationship estimated across a period containing one crash), surveying
  (adjusting a network of measurements).
ASKED-AS: least squares regression line best fit why squared outlier leverage drags sensitive

ESSENCE: a regression predicts the AVERAGE outcome for a given input, not
  the outcome. The scatter around the line does not shrink because you
  fitted a line through it — and for an individual case, that scatter is
  the whole of what matters.
ROOT: this file / a summary discards spread — a fitted line is a summary
  of the centre and says nothing about the width.
THREAD: medicine (a survival curve for a group against a patient's
  prospects), money (an expected return against an actual year), education
  (a predicted grade for a cohort against a pupil).
ASKED-AS: regression prediction individual average scatter around line interval wider person not group

ESSENCE: the leftovers are where the diagnosis lives. If the model has
  caught everything systematic, what remains should look like
  structureless noise — so any pattern in it is a message about what the
  model missed.
ROOT: premise — a model plus its leftovers reconstruct the data exactly,
  so anything the model failed to capture is sitting in the leftovers by
  construction.
THREAD: engineering (a fault visible in what a control model fails to
  predict), medicine (a subgroup showing up as a systematic error), money
  (a strategy whose errors cluster in one regime).
ASKED-AS: residuals check plot pattern left over model missed random scatter diagnostics fit

ESSENCE: a fitted relationship is only entitled to speak within the range
  of data that produced it. Outside that range the shape was never tested,
  and a straight line fitted to a gentle curve is at its most confident
  exactly where it is most wrong.
ROOT: this file / a model is a summary of the data it saw — and it has
  seen nothing outside its own range.
THREAD: engineering (a material model used beyond its tested loads), money
  (a risk model calibrated on calm years), public health (a dose curve
  extended below the doses studied).
ASKED-AS: extrapolation outside range data predict beyond dangerous model confident wrong straight

ESSENCE: adding more predictors always improves the fit to the data you
  have, even when the predictors are pure noise. So a rising fit score is
  not evidence of anything — it is arithmetic, and it is guaranteed.
ROOT: mathematics / more free parameters means a larger family of curves
  to choose the best from, and a larger family cannot contain a worse
  best.
THREAD: engineering (a model with a knob for every observation), money (a
  strategy with a rule for every past loss), science (a theory amended
  once per anomaly).
ASKED-AS: adding variables improves fit always r squared increases meaningless more parameters penalty

ESSENCE: with as many free numbers as data points, any model fits
  perfectly and predicts nothing. It has memorised the noise, and noise
  does not repeat — so the better the fit to the past, past a point, the
  worse the performance on the future.
ROOT: this file / a sample carries both signal and scatter, and a flexible
  enough model cannot tell them apart.
THREAD: money (a trading rule tuned on the history it is tested on),
  computing (a learned model memorising its training set), teaching (a
  pupil drilled on the exam paper).
ASKED-AS: overfitting memorise noise perfect fit useless prediction too many parameters generalise

ESSENCE: cross-validation buys an honest estimate by fitting on part of
  the data and scoring on the rest, several ways round. It works exactly
  as long as no information from the held-out part touched the fitting —
  and that is easier to violate than it looks.
ROOT: this file / only unseen data can report overfitting — so the
  discipline is to manufacture unseen data by withholding it.
THREAD: computing (leakage as the commonest error in applied learning),
  medicine (a score developed and validated on overlapping populations),
  money (a backtest whose universe was chosen with hindsight).
RULE: to validate a model honestly — split the data before doing anything
  else at all, including cleaning, scaling and choosing which variables to
  use; fit only on the part you kept; score once on the part you withheld;
  if the data has a time order, always fit on the earlier part and score
  on the later; and if you change the model after seeing that score, the
  score is spent and a fresh withheld part is needed.
ASKED-AS: cross validation holdout train test split leakage cheating honest estimate time

ESSENCE: no amount of data settles a causal question by itself. The same
  pattern of association is produced by several different causal stories,
  and choosing between them requires assumptions brought in from outside
  the numbers.
ROOT: premise — data records what went together, and causation is a claim
  about what would have happened otherwise, which was never observed.
THREAD: public health (an association argued about for decades), economics
  (a policy effect inferred from history), medicine (why trials exist at
  all).
ASKED-AS: correlation causation data alone cannot prove assumptions needed counterfactual what would have

ESSENCE: a common cause makes two effects move together although neither
  touches the other. Ice cream sales and drownings rise together because
  of summer — and the association is completely real, completely
  measurable, and completely useless as a lever.
ROOT: this file / association arises from any shared path, and a shared
  ancestor is a path.
THREAD: public health (the healthy-user problem), economics (a policy
  adopted by the places already improving), medicine (a treatment given to
  the patients most likely to do well).
ASKED-AS: confounding common cause third variable spurious association ice cream drowning adjust

ESSENCE: conditioning on a COMMON EFFECT manufactures an association out
  of nothing. Look only at the patients admitted to hospital, or only at
  the products that sold, and two unrelated causes will appear linked
  because either one alone was enough to get in.
ROOT: this file / conditioning restricts to a smaller room — and a room
  defined by a shared consequence is populated by trade-offs.
THREAD: medicine (associations found only among hospital patients),
  business (talent and looks appearing to trade off among the famous),
  science (findings visible only among published studies).
ASKED-AS: selection bias collider conditioning common effect hospital admitted spurious link adjusting worse

ESSENCE: randomising the assignment is the only device that balances the
  things nobody thought to measure. It does not make the groups identical;
  it makes any remaining difference a known quantity with a computable
  size.
ROOT: this file / a random split has a known sampling distribution — so
  the imbalance it leaves is exactly the noise that the inference already
  accounts for.
THREAD: medicine (the controlled trial), public health (a programme
  allocated by lottery), agriculture (where the whole technique was
  invented, on field plots).
ASKED-AS: randomised trial why gold standard balances unknown factors adjustment cannot assignment lottery

ESSENCE: a treatment can look better in every subgroup and worse overall,
  because the combined figure is a weighted blend and the weights differ.
  Worse: splitting by a further variable can reverse it back again, and
  there is no last table.
ROOT: mathematics / combining two ratios is a weighted average, and
  unequal weights can put the blend anywhere between them.
THREAD: medicine (a hospital with worse survival because it takes worse
  cases), law (hiring fair in every department and unfair overall), sport
  (a better rate every month and a worse season).
ASKED-AS: simpson paradox reverses subgroups overall which table correct split aggregate causal

ESSENCE: survival analysis exists because most people in the study have
  not had the event yet. Their time counts as information — they were
  followed this long without it — and throwing them out or treating them
  as failures both bias the answer badly.
ROOT: premise — a partial observation is still an observation, and the
  method must be built to use one rather than to discard it.
THREAD: engineering (component lifetimes with units still running),
  business (customer tenure with customers still subscribed), law (time to
  reoffending among those not yet reoffended).
ASKED-AS: survival analysis censored still alive not yet happened dropped out follow up

ESSENCE: the hazard is the chance of the event in the next moment given
  survival so far, and it can change with time. Risk that is high early,
  flat in the middle and rising at the end is a wholly different object
  from an average lifetime.
ROOT: this file / conditional probability — the hazard is a conditional
  rate, computed among those still at risk.
THREAD: engineering (infant mortality and wear-out in components),
  medicine (recurrence risk that peaks and falls), business (customer
  churn concentrated in the first months).
ASKED-AS: hazard rate risk over time early late failure bathtub curve average lifetime

ESSENCE: missing data is rarely missing at random. The people who did not
  reply, the machines that failed before recording, the patients who
  stopped attending — their absence is usually caused by the very thing
  being measured, so the gap is a signal and not a hole.
ROOT: this file / conditioning on availability is conditioning on a
  consequence, which biases whatever caused it.
THREAD: polling (non-response concentrated in particular groups), medicine
  (patients who dropped out because the treatment failed), engineering
  (sensors whose failure correlates with the event of interest).
ASKED-AS: missing data not at random dropouts nonresponse bias complete cases fill in

ESSENCE: the two schools disagree about what a probability is attached to.
  One says only to repeatable events, so a fixed unknown quantity has no
  probability and the method's reliability is what is guaranteed. The
  other attaches it to belief, so anything unknown may carry one.
ROOT: premise — probability is a measure obeying three rules, and the
  rules do not say what may be measured; that is a philosophical choice
  laid on top.
THREAD: law (a standard of proof against a degree of belief), medicine (a
  test's operating characteristics against a patient's odds), computing
  (both approaches used side by side and argued about).
ASKED-AS: bayesian frequentist difference prior belief long run which correct two approaches

ESSENCE: a prior is not a weakness of the Bayesian approach, it is the
  part that is written down. Every analysis contains prior commitments —
  which model, which variables, which comparison — and the argument is
  only about whether they are stated in the open.
ROOT: this file / updating requires a starting belief — and an analysis
  claiming none has made one implicitly.
THREAD: law (a presumption stated in the rules against an unstated one),
  science (a model choice functioning as a hidden assumption), engineering
  (design assumptions declared in a specification).
ASKED-AS: prior subjective bias bayesian criticism assumptions hidden objective data speak itself

ESSENCE: the largest question in statistics is almost never which test to
  run. It is who was measured, who was missed, what was recorded, and why
  those and not others — and a flawless analysis of a badly gathered set
  of numbers is a precise wrong answer.
ROOT: premise — every inference is about a population, and the link
  between the data and that population is made by the sampling, not by the
  arithmetic.
THREAD: polling (famous failures caused entirely by who could be reached),
  medicine (trials run on populations unlike the patients treated),
  history (records that survived because of what they were).
ASKED-AS: how data collected sampling who was asked missed matters more than test

ESSENCE: when the algebra refuses, simulate. Generate the situation many
  thousands of times with a machine, count how often the thing of interest
  happens, and read the answer off the count — an exact question answered
  by brute repetition.
ROOT: this file / the long-run proportion converges to the true chance —
  so a computer running the experiment is a legitimate way to evaluate a
  probability.
THREAD: engineering (reliability of a system too tangled to solve), money
  (portfolio outcomes under many futures), physics (calculations done by
  random sampling because no formula exists).
ASKED-AS: simulation monte carlo run many times computer estimate probability instead of formula
