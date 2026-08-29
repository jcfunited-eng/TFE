# 138 DEEP CALCULUS — change and accumulation
Two questions that look unrelated — how fast is it going right now, and
how much has piled up altogether — turn out to be the same question read
in opposite directions. Everything here is a consequence of that, and
almost everything moving has been described with it since.

ESSENCE: calculus asks two questions. How fast is this changing at this
  exact instant, and how much has accumulated over this whole stretch. The
  astonishment of the subject is that these are the same question running
  in opposite directions.
ROOT: premise — a rate and a total are two views of one process, one taken
  at a moment and one taken over a span.
CANNOT: no answering either question with ordinary arithmetic — an instant
  has no duration to divide by, and a changing rate has no single value to
  multiply. Both need a new machinery, and it is the same machinery.
THREAD: money (a balance against the rate it earns), physics (position
  against speed), the body (a dose rate against the total delivered).
ASKED-AS: what is calculus for two parts differentiation integration why invented change total

ESSENCE: a limit says where a process is heading, whether or not it ever
  arrives. It deliberately does not consult the value at the destination —
  only the approach — which is exactly what lets it answer questions the
  destination itself refuses.
ROOT: mathematics / infinity is a process — a limit is that process given
  a definite answer without ever finishing.
CANNOT: no limit that depends on the value at the point; the point is
  skipped by design. And no limit at all where the two approaches disagree
  — arriving from the left and the right at different values means the
  question has no answer.
THREAD: physics (a terminal speed approached forever), money (a fee
  structure approaching a floor), the living world (a population settling
  toward a carrying capacity).
ASKED-AS: limit approaches tends to never reaches left right value at point

ESSENCE: the reason the limit was needed: an instantaneous rate is a
  distance divided by a time, and at an instant both are nothing. Nothing
  over nothing has no value. The limit sidesteps this by asking what the
  ratio approaches as the gap shrinks, never letting it close.
ROOT: arithmetic / nothing divided by nothing has every answer at once —
  so the quotient must be approached rather than evaluated.
CANNOT: no computing an instantaneous rate by shrinking the gap to nothing
  and then dividing. The gap must stay positive throughout and the answer
  must come from the trend, or the arithmetic collapses.
THREAD: physics (a speedometer reading, which is a genuine limit), law (a
  rate defined over an interval that must be made precise), computing (a
  numerical derivative and the step size that must not be too small).
ASKED-AS: instantaneous rate zero over divided by nothing why limit needed speed moment

ESSENCE: a function is continuous where a small change in the input can
  only cause a small change in the output — no jumps, no holes. It is the
  formal version of being able to draw it without lifting the pen.
ROOT: this file / a limit — continuity says the limit exists AND agrees
  with the value there, which is two conditions and not one.
CANNOT: no jumping without a cause somewhere in the setup — so a
  discontinuity is always news: a price step, a phase change, a rule that
  switches at a threshold. And no guessing between measurements across a
  jump.
THREAD: money (a tax band where the rate steps), physics (water becoming
  ice at one temperature), engineering (a switch, which is deliberately
  discontinuous).
ASKED-AS: continuous function no jumps holes draw without lifting pen break discontinuity

ESSENCE: a continuous path from below a value to above it must pass
  through that value. That sounds obvious and it is a theorem — and it is
  what guarantees a solution exists between two test points, before anyone
  has any idea where.
ROOT: this file / continuity forbids jumps — so there is no way past a
  value except through it.
CANNOT: no continuous crossing that skips a level, so no continuous
  function positive at one end and negative at the other without a root
  between. And no such guarantee for a jumping function; the whole
  argument evaporates.
THREAD: navigation (a route that must cross a boundary line somewhere),
  computing (bisection search for a root, which is this theorem
  mechanised), physics (a rocking chair on a bumpy floor that can always
  be turned to sit still).
ASKED-AS: intermediate value theorem must cross between positive negative root exists somewhere guaranteed

ESSENCE: the derivative is the rate at an instant — how fast the output is
  changing per unit of input, right now. It is a whole new function built
  from the old one, giving that rate at every point.
ROOT: this file / the limit of a ratio as the gap shrinks — the rate is
  what that ratio approaches.
CANNOT: no derivative of a number; only of a relationship. And no reading
  a value off a derivative — knowing how fast a car is going says nothing
  about where it is, which is exactly the information the differentiating
  threw away.
THREAD: physics (velocity from position, acceleration from velocity),
  money (marginal cost as the rate at which total cost rises), medicine
  (how fast a level is falling rather than what it is).
ASKED-AS: derivative what is rate of change instant speed function slope dy dx

ESSENCE: the same number is the slope of the tangent — the straight line
  that grazes the curve at that point. Rate and slope are one quantity
  because a graph turns a rate into a steepness.
ROOT: geometry / slope is a rate wearing a picture — and calculus supplies
  the slope where the curve is not straight.
CANNOT: no tangent line crossing the curve at that point in general —
  though it may cross elsewhere, and at an inflection it crosses right
  there. The old idea that a tangent touches once belongs to circles only.
THREAD: engineering (reading a rate off a chart's steepness), money (the
  gradient of a growth curve), navigation (the heading as the tangent to
  the track).
ASKED-AS: tangent line slope curve derivative graph steepness touching gradient point picture

ESSENCE: a function has a derivative somewhere only if it is smooth there.
  At a corner the slope arriving from the left disagrees with the slope
  arriving from the right, so there is no single answer and the derivative
  simply does not exist.
ROOT: this file / a limit requires both approaches to agree — a corner is
  precisely the case where they do not.
CANNOT: no derivative at a corner, a cusp, or a vertical tangent — dead,
  not merely awkward. And no differentiability without continuity, though
  the reverse fails: continuous-but-nowhere-smooth functions exist and are
  the typical case, not the exception.
THREAD: engineering (a stress concentration at a sharp corner, which is
  this fact in steel), physics (a shock front where smoothness fails),
  finance (a price series with no meaningful instantaneous rate).
ASKED-AS: differentiable corner sharp point not smooth absolute value no derivative why

ESSENCE: the tangent is the best straight-line stand-in for a curve near a
  point, and that is what the derivative is really FOR. Almost every
  applied use of calculus is replacing something complicated by a straight
  line over a small enough stretch.
ROOT: this file / the derivative is the slope at a point — so the line
  through that point with that slope matches the curve to first order.
CANNOT: no straight approximation staying good far from the point; the
  error grows with the square of the distance, so doubling the range
  quadruples the mistake. Nothing warns you when it has gone bad.
THREAD: engineering (small-signal analysis, which linearises everything),
  navigation (a flat-earth approximation over a few miles), physics (a
  pendulum's simple behaviour, true only for small swings).
ASKED-AS: linear approximation tangent line estimate near point small changes error grows

ESSENCE: multiply a rate by a small change in the input and you get the
  approximate change in the output. That one sentence is how measurement
  errors are pushed through formulas, and how sensitivity is judged
  without ever recomputing.
ROOT: this file / the tangent is the best straight stand-in — so over a
  small step the curve and its tangent agree closely enough to use.
CANNOT: no error propagation through a place where the derivative is huge
  — the amplification is real, and it is why some formulas are unusable
  near certain values however precise the inputs.
THREAD: engineering (tolerance stack-up in an assembly), science (how a
  measurement's uncertainty travels into a result), money (how sensitive a
  valuation is to one assumption).
ASKED-AS: small change effect estimate error propagation sensitivity how much does affect

ESSENCE: the power rule says a power's rate is the power out front and one
  less upstairs. It is not a decree — expand a slightly larger input, and
  the leading leftover term is exactly that, with everything else too
  small to survive the shrinking.
ROOT: algebra / expanding a bracket — the crossing terms are what the
  derivative keeps, and the higher ones vanish in the limit.
CANNOT: no power rule for a variable exponent — two to the x is not x
  times two to the x minus one, because the rule was derived with the
  power held fixed. That case needs the exponential's own rule.
THREAD: geometry (a circle's area whose rate against radius is its
  circumference, which is not a coincidence), physics (energy against
  speed), money (a cost rising with a power of volume).
ASKED-AS: power rule bring down subtract one derivative x squared proof why works

ESSENCE: rates add. The derivative of a sum is the sum of the derivatives,
  and a constant multiplier comes straight through — because two things
  changing side by side change the total by exactly their two
  contributions.
ROOT: premise — accumulation and rate both respect adding, so anything
  built by adding can be differentiated piece by piece.
CANNOT: no such simplicity for a product or a quotient; those get their
  own rules precisely because a product is not built by adding. Assuming
  otherwise is the commonest error in the subject.
THREAD: money (total income as the sum of several streams, each with its
  own rate), physics (net force as a sum of forces), engineering (a
  system's response as a sum of independent responses).
ASKED-AS: derivative of a sum add separately constant multiple rule linearity simple why

ESSENCE: when two things are multiplied and both are changing, the total
  changes by each one's growth times the other's current size. Picture a
  rectangle growing on both sides: two new strips, and the tiny corner is
  too small to count.
ROOT: geometry / a rectangle's area is its two sides multiplied — so the
  growth of the area is the two strips added along the two edges.
CANNOT: no product rule that is simply the product of the derivatives —
  test it on x times x, where the truth is two x and the wrong rule gives
  one. The corner term is what vanishes, not the strips.
THREAD: money (revenue as price times quantity, with both moving), physics
  (momentum as mass times velocity for a leaking rocket), the living world
  (population times output per head).
ASKED-AS: product rule two functions multiplied derivative first times second plus rectangle

ESSENCE: the quotient rule is the product rule applied to a thing
  multiplied by an upside-down thing. The minus sign in it is doing one
  job only — recording that when the bottom grows, the whole fraction
  shrinks.
ROOT: this file / the product rule plus the chain rule, applied to the
  bottom raised to the power minus one.
CANNOT: no quotient rule needed where the bottom is a plain constant —
  that is a constant multiplier and the simple rule serves. Reaching for
  the heavy rule there is the classic waste.
THREAD: money (a ratio whose top and bottom both move, such as cost per
  unit), physics (density as mass over volume with both changing),
  medicine (a level per body weight in a growing child).
ASKED-AS: quotient rule fraction derivative bottom squared minus sign remember why order

ESSENCE: the chain rule is rates multiplying. If a wheel turns twice for
  each turn of a handle, and a belt moves three metres for each turn of
  the wheel, the belt moves six metres per turn of the handle — and that
  is the whole of it.
ROOT: premise — rates compose by multiplying, exactly as gear ratios and
  unit conversions do, because the middle units cancel.
CANNOT: no differentiating anything nested without it — and no forgetting
  the inner rate, which is the single most common mistake in the subject,
  because the answer looks complete without it.
THREAD: engineering (gear trains and their combined ratio), money (a
  currency conversion through a third currency), the body (a drug's effect
  through a chain of intermediate levels).
ASKED-AS: chain rule inside outside derivative nested function gears multiply rates forget

ESSENCE: there is one function that is its own rate of change — it grows
  exactly as fast as it currently is. That property is not a curiosity of
  a chosen number; the number e is DEFINED by it, and everything else
  about exponentials follows.
ROOT: this file / the derivative as a rate — asking which function
  satisfies "rate equals amount" produces a single family, and one member
  of it starts at one.
CANNOT: no other base with this exact property; every other exponential's
  rate is itself times a constant, and that constant is one only for e.
  Which is why e appears unbidden in growth, decay, interest and
  probability.
THREAD: money (continuously compounded interest), physics (radioactive
  decay), the living world (unchecked population growth).
ASKED-AS: e number derivative itself exponential why special natural growth rate equals

ESSENCE: the logarithm's rate is one over the input. So a log climbs fast
  when small and crawls when large — which is exactly the behaviour that
  makes it a scale for things spanning many multiplications.
ROOT: this file / inverse functions have reciprocal slopes — the
  exponential's steepness upside down is the logarithm's flatness.
CANNOT: no logarithm of nothing or below, so no rate there — the curve
  falls away without bound as the input approaches nothing. And no bounded
  log: it climbs forever, just very slowly.
THREAD: the body (senses that respond to ratios, so equal steps of
  sensation are equal multiples of stimulus), money (utility of an extra
  pound falling with wealth), computing (the cost of halving searches).
ASKED-AS: derivative of log one over x why slows down grows forever slowly

ESSENCE: sine's rate is cosine and cosine's rate is minus sine, so
  differentiating four times returns you to where you started. That
  four-step cycle is why these functions describe everything that goes
  round and comes back.
ROOT: this file / the derivative as a rate, applied to a point moving
  round a circle at steady speed — its two coordinates chase each other
  exactly this way.
CANNOT: no such clean rule in degrees — the derivative picks up an ugly
  constant, and that alone is the reason radians are compulsory in
  calculus rather than merely tidy.
THREAD: physics (a mass on a spring, where acceleration is minus
  displacement), music (the shape of a pure tone), engineering
  (alternating current, where the same cycle appears as a phase shift).
ASKED-AS: derivative of sine cosine minus cycle four times radians degrees why must

ESSENCE: an inverse function's slope is the reciprocal of the original's
  slope at the matching point — because reflecting a graph swaps across
  and up, and swapping rise with run turns a slope upside down.
ROOT: algebra / an inverse is the machine run backwards — and the picture
  of that is the graph reflected in the diagonal.
CANNOT: no inverse slope where the original's slope is nothing — a flat
  spot reflects into a vertical one, and vertical has no slope. That is
  precisely where the inverse stops being differentiable.
THREAD: engineering (a sensor's calibration curve read backwards),
  economics (demand as a function of price and price of quantity),
  navigation (a conversion table used in either direction).
ASKED-AS: inverse function derivative reciprocal slope flip graph reflection vertical tangent flat

ESSENCE: when a relationship refuses to be untangled into one letter
  alone, differentiate it as it stands, treating the dependent letter as a
  function of the other and applying the chain rule every time it appears.
  No untangling needed, and often none possible.
ROOT: this file / the chain rule — the dependent letter is a function, so
  every appearance of it carries its own inner rate.
CANNOT: no explicit formula for many perfectly good curves — a circle
  needs two branches, and messier relations need none at all. Implicit
  differentiation is not a shortcut; it is often the only route.
THREAD: engineering (a constraint relating several quantities with none
  isolated), physics (a conserved relation differentiated to find how the
  parts must move), economics (an equilibrium condition).
ASKED-AS: implicit differentiation dy dx circle cannot solve for y treat function chain

ESSENCE: when several quantities are tied by a relation and one is
  changing, the others must change at rates the relation dictates. A
  ladder's foot sliding out forces the top down at a rate that grows
  without bound as it nears the ground.
ROOT: this file / the chain rule — differentiating a relation with respect
  to time turns a geometric fact into a statement about rates.
CANNOT: no rate for a quantity the relation does not involve. And no
  substituting the particular numbers before differentiating — do that and
  the moving quantities become constants and their rates vanish, which is
  the standard wreck.
THREAD: engineering (a linkage where one joint's speed sets another's),
  medicine (a volume changing as a pressure does), weather (a rate of
  cooling tied to a rate of rising).
ASKED-AS: related rates ladder sliding balloon inflating how fast other changing chain

ESSENCE: the derivative of a derivative measures how the rate itself is
  changing. It tells you the bending: positive means the curve is holding
  water, negative means it is shedding it, and in motion it is
  acceleration — what a body actually feels.
ROOT: this file / a derivative is itself a function, so it can be
  differentiated in its turn, and there is no reason to stop.
CANNOT: no sensing speed, only changes in it — a passenger in a smooth
  aircraft cannot feel five hundred miles an hour, which is a statement
  about the second derivative and not the first, and it is why the first
  is unmeasurable from inside.
THREAD: physics (force is mass times the second derivative, so the laws of
  motion are second-order), money (inflation falling while prices still
  rise), driving (comfort determined by the third derivative, the jerk).
ASKED-AS: second derivative meaning acceleration curvature concave up down bending feel motion

ESSENCE: where the rate is positive the function climbs, where negative it
  falls, and it can only turn where the rate passes through nothing or
  fails to exist. That single sentence converts the shape of any curve
  into a sign question.
ROOT: this file / a continuous rate cannot change sign without passing
  through nothing — the intermediate value theorem applied to the
  derivative.
CANNOT: no turning point where the derivative is defined and non-zero,
  which prunes the search entirely. But no guarantee the reverse: a rate
  of nothing may be a flat spot on a climb rather than a turn.
THREAD: money (a peak in a curve where the marginal figure hits nothing),
  physics (a ball at the top of its flight), medicine (a level that has
  stopped rising but has not yet begun to fall).
ASKED-AS: increasing decreasing derivative positive negative turning point where zero sign

ESSENCE: a maximum or minimum can only occur where the derivative is
  nothing, where it does not exist, or at an endpoint. That is the whole
  candidate list — everywhere else the function is going somewhere, and
  something going somewhere is not at an extreme.
ROOT: this file / a rate other than nothing means the value can be
  improved by stepping in the favourable direction.
CANNOT: no interior extreme with a non-zero derivative. But no assuming
  every zero-derivative point is an extreme, and no forgetting the
  endpoints — the endpoint case is where most real optimisations actually
  land, and it is the one always left off.
THREAD: money (a best price at a boundary of what the market allows),
  engineering (a design at the edge of a permitted range), sport (an
  effort level capped by a rule rather than by physiology).
ASKED-AS: maximum minimum critical points derivative zero endpoints candidates find optimum where

ESSENCE: two tests decide which kind of turning point you have. The first
  watches the rate change sign around it and always works. The second
  reads the bending at the point, is quicker, and says nothing at all when
  the bending is also nothing.
ROOT: this file / the sign of the rate says climbing or falling, and the
  sign of the bending says which way the curve is holding.
CANNOT: no verdict from the second test when the second derivative is
  nothing there — the point may be a peak, a trough, or neither, and only
  the first test can settle it.
THREAD: medicine (a quick test that is sometimes uninformative against a
  slower one that always answers), engineering (a rule of thumb with a
  known blind spot), law (a summary procedure that must fall back to full
  hearing).
ASKED-AS: first second derivative test maximum minimum which inconclusive zero sign change

ESSENCE: a continuous function on a closed stretch always attains a
  highest and a lowest value somewhere on it. Open the ends or break the
  continuity and that promise vanishes — which is why the conditions are
  stated so carefully.
ROOT: this file / continuity plus a closed range leaves the function
  nowhere to escape to.
CANNOT: no guaranteed maximum on an open range — a value can climb toward
  a boundary it never reaches, so the best is approached and never
  attained. Optimisation problems that fail this way are not badly solved;
  they have no answer.
THREAD: money (a bid that can be improved indefinitely toward a limit
  never touched), engineering (a design where the optimum sits exactly at
  a forbidden boundary), law (an award that must be a definite figure).
ASKED-AS: extreme value theorem closed interval maximum exists open no highest attained boundary

ESSENCE: an inflection is where the bending reverses — the curve stops
  holding water and starts shedding it. It is not a peak or a trough; the
  function may be climbing throughout. It is the point where growth stops
  accelerating and begins to ease.
ROOT: this file / the second derivative measures bending — so an
  inflection is where that quantity changes sign.
CANNOT: no inflection where the second derivative merely touches nothing
  without crossing; the sign must genuinely change. And no inflection
  visible in the value alone — only in the shape.
THREAD: public health (an epidemic whose daily cases are still rising but
  no longer faster, which is the turning point people actually mean),
  money (growth slowing while totals still climb), the living world (the
  midpoint of a growth curve).
ASKED-AS: inflection point curve changes bending concave second derivative zero epidemic peak

ESSENCE: an optimisation problem is nearly always won at the setup. Write
  the quantity to be made best in terms of ONE variable, using the
  constraint to eliminate the rest — and then the calculus is three lines.
  Without that step there is nothing to differentiate.
ROOT: this file / an extreme sits where the rate vanishes — but a rate
  requires exactly one thing to vary.
CANNOT: no optimising a quantity of two free variables by one derivative;
  the constraint is not an obstacle, it is the equipment that makes the
  problem solvable at all. An unconstrained best is usually infinite and
  therefore useless.
THREAD: engineering (least material for a required strength), money
  (maximum profit subject to capacity), farming (best yield for the water
  available).
RULE: to solve an optimisation problem — draw it and name every quantity;
  write the thing to be maximised or minimised as a formula; write the
  constraint as a second equation; use the constraint to remove all but
  one variable; differentiate, set to nothing, and solve; then test the
  candidates AND the endpoints, and answer in the original words.
ASKED-AS: optimisation largest smallest box fence maximise area constraint one variable steps

ESSENCE: over any smooth stretch, there is at least one moment where the
  instantaneous rate exactly equals the average rate for the whole
  stretch. If you averaged sixty miles an hour, you were doing sixty at
  some instant — provably.
ROOT: this file / a smooth journey that ends up somewhere must at some
  point have been going at the rate that would take it there.
CANNOT: no smooth motion that stays always above or always below its own
  average rate. Which is why speed cameras at two points can convict on
  arithmetic alone, with no measurement of instantaneous speed at all.
THREAD: law (average speed enforcement, resting on this theorem), money (a
  return that must have been achieved at some instant), sport (a pace hit
  at least once during a run).
ASKED-AS: mean value theorem average speed at some point actually going proof cameras

ESSENCE: to hunt a root, take a guess, slide down the tangent to where it
  crosses, and use that as the next guess. It converges astonishingly fast
  when it works — roughly doubling the correct digits each step — and
  wanders off entirely when it does not.
ROOT: this file / the tangent is the best straight stand-in — so the
  tangent's root is a good estimate of the curve's root.
CANNOT: no convergence guaranteed from any starting point; a flat spot
  flings the guess far away and some starts cycle forever. Speed here is
  bought with reliability, which is the standing trade in numerical work.
THREAD: computing (how square roots and divisions are actually computed in
  hardware), engineering (solving equations with no formula), navigation
  (iterating a position fix).
RULE: to find a root by this method — choose a starting guess near where
  you believe the root is; compute the function and its derivative there;
  take the guess minus the function divided by the derivative as the new
  guess; repeat until the change is smaller than you care about; and if
  the guesses start growing or oscillating, abandon and restart elsewhere.
ASKED-AS: newton method root finding iteration tangent guess converge fast fails diverge

ESSENCE: undoing a derivative gives not one answer but a whole family, all
  differing by a constant — because a constant has no rate, so no rate can
  report one. The lost constant is real information that must come from
  somewhere else.
ROOT: this file / differentiating destroys the starting value — and no
  operation recovers what was destroyed.
CANNOT: no recovering the constant from the rate, ever. Which means every
  physical use of an antiderivative needs one measured condition — a
  starting position, an initial balance, an initial temperature — or the
  answer is a family and not a prediction.
THREAD: navigation (dead reckoning needs a known starting point), medicine
  (a rate of loss needs a starting level), accounting (a flow statement
  needs an opening balance).
ASKED-AS: plus c constant integration why family antiderivative initial condition lost information

ESSENCE: an integral is accumulation — adding up an amount that keeps
  changing, over a stretch where it changes. It is the answer to "how much
  altogether" when the rate would not sit still long enough to be
  multiplied.
ROOT: premise — a total is a sum of contributions, and when the
  contributions vary continuously the sum must become a limit of sums.
CANNOT: no total from rate times time when the rate moves. And no
  accumulation without saying over WHAT — the same integrand accumulated
  over distance, time or angle answers three different questions with
  three different units.
THREAD: money (total interest earned at a varying rate), physics (work
  done by a varying force), medicine (total exposure to a changing
  concentration).
ASKED-AS: integral accumulation total amount adding up varying rate over time how much

ESSENCE: draw the rate as a curve and the accumulated total is the area
  underneath it. Area below the axis counts as negative — which is not a
  convention but the honest bookkeeping of a rate that has turned round
  and is now taking away.
ROOT: this file / accumulation is a sum of contributions — each
  contribution is a thin strip, and a strip's height is a rate while its
  width is a step.
CANNOT: no reading total distance travelled off a signed area when the
  motion reversed — the signed answer gives displacement, and total
  distance needs the absolute value integrated instead. Two different
  questions, routinely confused.
THREAD: money (a cash flow chart where outflows are area below the line),
  physics (displacement against distance travelled), engineering (net
  against gross accumulation).
ASKED-AS: integral area under curve negative below axis signed displacement distance difference meaning

ESSENCE: the definition is a sum of thin strips whose widths shrink toward
  nothing while their number grows without bound. Everything else in
  integration is machinery for evaluating that limit without actually
  performing it.
ROOT: mathematics / infinity is a process — the sum is never completed,
  only approached, and the limit is what is meant by the integral.
CANNOT: no strip width small enough to be exact; the answer only exists as
  the limit. And no such limit for functions wild enough that the strips
  disagree depending on where inside each one you sample.
THREAD: engineering (numerical integration, which really does add the
  strips), computing (approximating an area by sampling), farming
  (estimating an irregular field by strips).
ASKED-AS: riemann sum rectangles strips limit definition integral approximate area width shrinks

ESSENCE: the fundamental theorem says the two questions are one. To
  accumulate a rate over a stretch, find any function whose rate it is,
  and subtract its values at the two ends. An infinite sum of strips
  becomes one subtraction.
ROOT: this file / accumulating a rate rebuilds the quantity — because the
  rate was what the quantity's changing produced in the first place.
CANNOT: no shortcut without an antiderivative, which is why so much effort
  goes into finding them. And no application of it across a discontinuity
  in the interval — the theorem's hypotheses are not decoration.
THREAD: money (a year's interest from opening and closing balances rather
  than daily sums), physics (work from a potential's endpoints, whatever
  the path), navigation (net displacement from start and finish alone).
ASKED-AS: fundamental theorem calculus connects derivative integral opposite subtract endpoints why works

ESSENCE: a definite integral is a number — an accumulation between two
  stated ends. An indefinite integral is a family of functions. They are
  written almost the same and they are different kinds of object, which is
  the source of endless confusion.
ROOT: this file / accumulation needs a stretch, while antidifferentiation
  needs none — the fundamental theorem links them without merging them.
CANNOT: no constant surviving in a definite integral; it cancels in the
  subtraction, which is why the ends make the answer unique. And no
  numerical answer from an indefinite one without supplying a condition.
THREAD: accounting (a period figure against a running ledger), physics (a
  change in energy against a potential function), medicine (dose delivered
  in a window against a cumulative curve).
ASKED-AS: definite indefinite integral difference limits number function constant cancels which use

ESSENCE: substitution is the chain rule run backwards. Spot an inner
  function whose rate is also sitting in the integrand, rename it, and the
  integral collapses into something plain. Almost every integral that
  yields at all yields to this first.
ROOT: this file / the chain rule multiplied by an inner rate — so an
  integrand carrying that inner rate is a chain rule waiting to be undone.
CANNOT: no substitution without the inner rate present, up to a constant.
  And no forgetting to change the limits when the variable changes, or the
  ends now refer to a quantity that is no longer there.
THREAD: cooking (a change of units that makes a recipe trivial), physics
  (a change of variable that straightens a problem), computing (a
  transformation applied to make a computation tractable).
RULE: to integrate by substitution — look for an inner function whose
  derivative also appears as a factor; name that inner function u; replace
  it and its derivative-times-dx by u and du; if the integral is definite,
  convert both limits into u as well; integrate in u, then either convert
  back or use the converted limits.
ASKED-AS: integration by substitution u sub chain rule backwards inner function change limits

ESSENCE: integration by parts is the product rule run backwards. It trades
  one integral for another, and the whole skill is choosing the swap so
  that the new one is easier — pick badly and it gets worse forever.
ROOT: this file / the product rule gives the rate of a product as two
  terms — rearranged, it says one integral equals a product minus the
  other integral.
CANNOT: no guarantee the traded integral is simpler; the method offers an
  exchange, not a solution. And no progress at all on some integrals
  however cleverly the parts are chosen — the trade can cycle back to
  where it began.
THREAD: negotiation (trading a problem for a different problem you would
  rather have), engineering (a change of formulation that moves the
  difficulty), computing (transforming a hard case into a known one).
ASKED-AS: integration by parts product rule backwards choose u dv which easier liate

ESSENCE: a rational function can be broken into a sum of simple fractions
  with the factors of the bottom underneath, and each piece then
  integrates on sight. The work is entirely in the algebra; the calculus
  at the end is the easy part.
ROOT: algebra / adding rational expressions builds a common bottom — this
  is that construction walked backwards.
CANNOT: no partial fractions until the top's degree is below the bottom's;
  divide first if it is not. And no such split without factoring the
  bottom, which for high degrees may itself be impossible in practice.
THREAD: engineering (a system's response split into simple modes),
  medicine (a decay curve separated into two independent processes), money
  (a cash flow decomposed into standard components).
ASKED-AS: partial fractions split rational function denominator factors integrate each piece method

ESSENCE: most functions have no antiderivative expressible in ordinary
  formulas. Not that nobody has found one — there is none, and it has been
  proved. The bell curve's own integral is the most famous case, and the
  whole of statistics uses a table because of it.
ROOT: mathematics / a set of tools defines a reachable set — and the
  elementary functions are such a set, with a boundary.
CANNOT: no elementary antiderivative for e to the minus x squared, for
  sine over x, and for endless ordinary-looking expressions. Dead, not
  undiscovered — which makes numerical integration a necessity rather than
  a shortcut.
THREAD: statistics (tables and software for the normal curve), physics
  (special functions named and tabulated because they had to be), geometry
  (an ellipse's perimeter, which has no elementary formula).
ASKED-AS: cannot integrate no antiderivative elementary proved impossible bell curve table numerical

ESSENCE: when no formula exists, add the strips numerically. Straight-top
  strips are crude, sloping tops are better, and curved tops better still
  — each refinement buys accuracy at the same cost, which is why nobody
  uses the crude one.
ROOT: this file / the integral is defined as a limit of sums — so
  computing a sum with small enough steps is not a cheat, it is the
  definition, stopped early.
CANNOT: no numerical method safe against a function that wiggles faster
  than the sampling; whatever is missed between samples is invisible and
  unbounded. Every such method assumes smoothness it cannot verify.
THREAD: engineering (areas and volumes from measured data), medicine (drug
  exposure computed from sampled blood levels), navigation (position
  accumulated from sampled speeds).
ASKED-AS: numerical integration trapezium simpson rule approximate area steps accuracy computer estimate

ESSENCE: an integral can run to infinity or over a point where the
  function blows up, and still come out finite. The area under one over x
  squared, all the way out, is exactly one — endless extent, bounded
  content.
ROOT: this file / an integral is a limit — so an infinite range is handled
  by taking a limit of finite ranges, not by any new idea.
CANNOT: no finite area under one over x itself, out to infinity — it
  diverges, though it looks barely different. The boundary between finite
  and infinite here is thin and unguessable, which is why it must be
  computed and never assumed.
THREAD: money (a payment stream lasting forever with a finite present
  value), physics (a field's total energy, finite or not depending on the
  power), astronomy (why a sky full of infinite stars is a real problem).
ASKED-AS: improper integral infinity finite area converges diverges one over x squared

ESSENCE: the average value of a changing quantity over a stretch is its
  accumulation divided by the length of the stretch. That is the ordinary
  meaning of average, with the sum replaced by an integral and the count
  by a length.
ROOT: this file / accumulation is a continuous sum — so dividing by the
  span is the continuous version of dividing by the count.
CANNOT: no averaging by sampling evenly unless the samples are dense
  enough — and no reading the average off the endpoints. A quantity that
  spent most of its time low and finished high averages low.
THREAD: money (average balance over a month deciding the interest),
  engineering (mean power from a fluctuating signal), weather (a mean
  temperature that no hour actually recorded).
ASKED-AS: average value of a function integral divided by length mean over interval

ESSENCE: to find a volume, slice the solid, write the area of a typical
  slice as a function of where it is cut, and accumulate. Any solid you
  can describe slice by slice is a solid you can measure, however odd its
  outside.
ROOT: this file / accumulation is a sum of thin contributions — with each
  contribution now a slab of thickness rather than a strip of width.
CANNOT: no volume from a formula for the outside alone; the slice areas
  are what the method eats. And no correct answer if the slices are taken
  in a direction where their shape cannot be written down.
THREAD: medicine (organ volume from a stack of scan slices), engineering
  (displacement of a hull from its sections), geology (the volume of a
  deposit from drilled sections).
ASKED-AS: volume by slicing solids revolution disks washers integrate cross section area

ESSENCE: the length of a curve is found by accumulating tiny straight
  pieces, each the hypotenuse of a small step across and a small step up.
  It is the right triangle law, applied a million times and summed.
ROOT: geometry / the straight-line distance between two near points, made
  continuous by shrinking the steps.
CANNOT: no arc length formula that is easy — the square root in it defeats
  elementary integration for most curves, including the ellipse. Curve
  length is where calculus routinely gives up and hands the job to a
  computer.
THREAD: navigation (distance along a winding route), engineering (belt or
  cable length over pulleys), geography (a coastline's length, which
  depends on the ruler and never settles).
ASKED-AS: arc length curve distance along formula square root hard integrate coastline

ESSENCE: a differential equation is a sentence about how something changes
  rather than about what it is. "It cools at a rate proportional to how
  much hotter it is than the room" is a complete physical law, and the
  temperature over time is what solving it produces.
ROOT: this file / a rate is a function in its own right — so a law can be
  stated about the rate and the quantity together.
CANNOT: no unique answer from the equation alone — it describes a family
  of behaviours, and one measured condition is required to pick out the
  actual one. A law without a starting state predicts nothing specific.
THREAD: physics (nearly every law is one of these), medicine (drug
  clearance), money (a balance whose growth depends on its size).
ASKED-AS: differential equation what is describes change rate law solve initial condition

ESSENCE: the order of a differential equation — whether it mentions the
  first rate, the second, or higher — decides how many facts must be
  supplied to pin the answer down. One for a first-order equation, two for
  a second, and so on, with no exceptions.
ROOT: this file / every antidifferentiation loses one constant, so every
  order costs one condition to recover.
CANNOT: no pinning a second-order behaviour with one condition — a thrown
  ball needs both where it started and how fast, and no amount of
  cleverness supplies the missing one.
THREAD: physics (position and velocity as the full state of a moving
  body), engineering (a control system's required initial state),
  computing (a simulation that cannot start without a full state).
ASKED-AS: order differential equation how many initial conditions second needs two position velocity

ESSENCE: when the equation can be arranged with everything about one
  quantity on one side and everything about the other on the other, both
  sides can simply be integrated. That single trick handles a surprising
  share of the equations that matter.
ROOT: this file / an integral undoes a rate — and once the variables are
  separated, each side is a rate with respect to its own variable.
CANNOT: no separation when the two quantities are tangled in a sum rather
  than a product — and most equations are so tangled. The method is
  narrow, which is why the subject grew so many others.
THREAD: chemistry (reaction rates depending only on concentration),
  medicine (elimination depending only on the amount present), physics
  (cooling depending only on the temperature difference).
RULE: to solve a separable equation — get all terms in one variable with
  its differential on one side and all terms in the other with its
  differential on the other; integrate both sides, putting a single
  constant on one of them; then use the given condition to fix the
  constant; finally rearrange if an explicit form is wanted.
ASKED-AS: separable differential equation separate variables integrate both sides method constant condition

ESSENCE: the simplest possible statement about change — the rate is
  proportional to the amount present — produces exponential growth when
  the constant is positive and exponential decay when it is negative. One
  sentence, and half the processes in nature.
ROOT: this file / the exponential is its own rate — so it is the solution
  of the very equation that says so.
CANNOT: no exponential decay reaching nothing in finite time, and no
  exponential growth that a limited world can sustain. Both statements are
  about the same equation, and both are why the model always eventually
  fails.
THREAD: physics (radioactive decay and its half-life), money (compound
  interest and debt), the living world (a population before anything
  limits it).
ASKED-AS: exponential growth decay half life proportional to amount differential equation solution

ESSENCE: add a ceiling and the equation changes character. Growth is
  proportional to the amount AND to how much room remains, so it starts
  exponential, bends at the halfway point, and levels off. The bend is the
  most informative moment in the whole curve.
ROOT: this file / the growth equation with a factor that closes as the
  ceiling is approached, so the rate is driven back to nothing.
CANNOT: no exceeding the ceiling from below, and no fitting the ceiling
  from early data — the early part of the curve is indistinguishable from
  pure exponential, which is why forecasts made early are always wrong
  about the limit.
THREAD: public health (an epidemic's course), the living world (a
  population meeting its food supply), business (adoption of a new product
  saturating a market).
ASKED-AS: logistic growth s curve ceiling limit levels off epidemic saturation midpoint bend

ESSENCE: when acceleration is proportional to displacement but pointed
  back toward the middle, the result is oscillation — an endless overshoot
  and return. That equation is a spring, a pendulum, a plucked string, and
  an electrical circuit, without changing a symbol.
ROOT: this file / sine's rate cycle — sine is the function whose second
  rate is minus itself, so it is the answer this equation demands.
CANNOT: no oscillation from a restoring force that pushes AWAY from the
  middle; that gives runaway growth instead, and the difference is a
  single sign. Stability and collapse are one sign apart.
THREAD: music (every instrument's sound production), engineering (any
  structure with stiffness and mass), physics (light and radio as
  oscillating fields).
ASKED-AS: simple harmonic motion spring pendulum oscillation restoring force sine solution why

ESSENCE: add friction and the oscillation fades; add a push at the right
  rhythm and it grows without limit. Damping and driving are two extra
  terms in the same equation, and between them they describe every
  vibration a body or a bridge ever suffers.
ROOT: this file / the oscillation equation, with one term proportional to
  speed and one supplied from outside.
CANNOT: no resonance without a matching rhythm — a random push does little
  however hard. And no escaping resonance by strength alone: the cure is
  damping or a change of frequency, never more material.
THREAD: engineering (bridges and buildings tuned away from their hazards),
  music (a resonant body making a string audible), medicine (imaging that
  excites tissue at its own frequency).
ASKED-AS: damping resonance driven oscillation bridge collapse frequency matching amplitude grows friction

ESSENCE: a smooth function can be rebuilt near a point from its value and
  all its rates there — value, slope, bending, and onward. The function's
  entire local behaviour is encoded in a list of numbers taken at a single
  place.
ROOT: this file / the tangent is the best straight fit — and adding the
  bending gives the best curved fit, and so on without end.
CANNOT: no such reconstruction for a function that is not smooth enough at
  the point, and no promise the rebuilt series matches away from it. There
  are functions all of whose rates vanish at a point and which are not
  zero anywhere else.
THREAD: computing (how a machine actually evaluates sine and exponential),
  physics (small-oscillation approximations everywhere), engineering (a
  model expanded about an operating point).
ASKED-AS: taylor series expansion function as polynomial derivatives at a point rebuild

ESSENCE: cutting that series short gives a polynomial that approximates
  the function, and the error is governed by the first term you threw
  away. More terms buys accuracy near the point and buys nothing far from
  it.
ROOT: this file / a series expansion is built at a point — so its
  authority fades with distance from that point, not with the number of
  terms.
CANNOT: no fixed number of terms good over an unbounded range. And no
  detecting the error from the approximation itself — the polynomial looks
  perfectly well behaved exactly where it has stopped being true.
THREAD: computing (floating-point routines with argument reduction to stay
  near the point), engineering (a linear model outside its validated
  range), money (a risk approximation that fails in the large moves that
  matter).
ASKED-AS: taylor polynomial approximation error remainder how many terms accurate near far

ESSENCE: an endless sum has a value only if its partial totals settle
  toward one. Terms shrinking toward nothing is necessary and not enough —
  the harmonic sum, one plus a half plus a third and onward, has terms
  going to nothing and a total that grows without bound.
ROOT: mathematics / infinity is a process — an endless sum is a sequence
  of finite totals, and it converges only if that sequence does.
CANNOT: no concluding convergence from shrinking terms. And no rearranging
  a conditionally convergent sum safely — reorder it and it can be made to
  total anything at all, which is as strange as arithmetic gets.
THREAD: money (a stream of shrinking payments that still totals
  infinitely), computing (an iterative method whose corrections shrink and
  never finish), physics (a sum over states that must be checked before it
  is trusted).
ASKED-AS: series converges diverges harmonic terms go to zero not enough sum infinite

ESSENCE: a partial derivative asks the slope in one chosen direction with
  everything else held still. There is no single slope on a hillside — the
  answer depends entirely on which way you decided to walk.
ROOT: geometry / dimension is how many directions there are — and a rate
  needs one of them nominated before it means anything.
CANNOT: no such thing as THE derivative of a function of several
  variables. And no combining partial rates by adding them naively; the
  direction matters and must be carried.
THREAD: economics (how profit responds to price with volume held fixed),
  weather (temperature falling with height at fixed position), engineering
  (sensitivity to one parameter at a time).
ASKED-AS: partial derivative one variable at a time hold others constant direction hillside

ESSENCE: collect the partial rates into an arrow and it points straight
  uphill, with its length the steepest slope available. Every
  hill-climbing method ever written follows it, and every descent method
  follows it backwards.
ROOT: this file / the dot product measures agreement of direction — the
  slope in any direction is that arrow dotted with it, and the largest
  such value is along the arrow itself.
CANNOT: no direction steeper than the gradient, and no slope at all along
  a direction square to it — which is why contour lines cross the gradient
  at right angles, always.
THREAD: computing (how machines are trained, by walking downhill on an
  error surface), geography (water running down the steepest line),
  physics (force as the downhill direction of a potential).
ASKED-AS: gradient vector steepest uphill direction contour perpendicular descent hill climbing slope

ESSENCE: a double integral accumulates over a region of a surface rather
  than along a stretch. Slice the region into strips, integrate along each
  strip, then integrate the strips — an accumulation of accumulations, and
  no new idea beyond that.
ROOT: this file / accumulation is a sum of contributions — with the
  contributions now patches instead of strips.
CANNOT: no swapping the order of integration without redrawing the region
  — the inner limits usually depend on the outer variable, and copying
  them across unchanged is the standard error. The VALUE is unchanged for
  well-behaved functions; the limits are not.
THREAD: engineering (mass and balance of a plate with varying density),
  statistics (probability over a two-dimensional spread), geography
  (rainfall totalled over a catchment).
ASKED-AS: double integral region area two variables order limits swap change region

ESSENCE: physics is written in calculus because its laws are statements
  about rates. Force sets acceleration, which is a second rate; fields
  change according to how they vary in space; and every conservation law
  is the statement that some rate is nothing.
ROOT: premise — nature's regularities are local and instantaneous, and the
  only language for a local instantaneous statement is a rate.
CANNOT: no law of motion expressible without rates — a table of positions
  is data, not a law, and it predicts nothing outside itself. And no
  prediction from the law alone without a measured starting state.
THREAD: engineering (every simulation integrating the same equations), the
  living world (population and metabolism modelled the same way), money
  (continuous-time models borrowed wholesale from physics).
ASKED-AS: why physics uses calculus laws rates newton equations motion describe nature language
