# 103 DEEP INFORMATION AND SECURITY — keeping and guarding what is known
Middle floors under file 19. Information's own laws are proved, not
discovered; guarding it adds a second party who is trying, and that
changes every calculation. Every entry carries its cannot-twin.

ESSENCE: surprise is measured against a model, so the same message
  carries different amounts to different receivers — a telegram
  that decides one reader's life is noise to the next; the quantity
  is in the meeting, not in the paper.
ROOT: computing (19) / information is surprise — this floor asks
  surprise to whom, and finds the question is not optional.
CANNOT: no information content without a receiver's expectations —
  "how much is in this file" has no answer until someone says to
  whom, which is why no measuring instrument can weigh a message
  by itself.
THREAD: teaching (a fact is worth what the student did not already
  have), markets (news is what the price had not already priced),
  medicine (a test result means different things by prior risk).
ASKED-AS: news matters someone else already knew boring surprise depends who reading useless important

ESSENCE: compression is prediction wearing a different hat — a
  method that guesses the next piece well can spend few bits saying
  which guess was right, so how well something compresses is a
  measure of how well it is understood.
ROOT: computing (19) / compression is essence-extraction — and
  extraction requires a model doing the extracting.
CANNOT: no unpacking without the same model that packed — the
  rulebook is part of the message, and it counts toward the size,
  which is why compressing a tiny file makes it larger and why a
  clever scheme with a huge table can cheat any single test.
THREAD: language (an in-joke is a compressed shared history, and
  useless outside it), the mind (an expert sees a board position as
  one thing; a beginner sees thirty-two pieces), science (a law).
ASKED-AS: zip file smaller already compressed jpeg wont shrink pattern predict guess model rulebook

ESSENCE: lossy throwing-away is aimed at a particular receiver — it
  discards what a human ear or eye is known to miss, which makes it
  honest for listening and dishonest anywhere the discarded part
  might matter.
ROOT: information is measured against a receiver (this file) — the
  thrower-away must assume who is looking, and does.
CANNOT: no recovering what lossy discarded — there is no
  "enhancing" it back, because the detail is not hidden but absent.
  And no free re-saving: each pass through a lossy step throws away
  again, so a copy of a copy degrades while a lossless copy never
  does.
THREAD: medicine (a compressed scan may lose the thing being looked
  for), law (an evidence copy must be lossless or it is not the
  evidence), memory (we store the gist and reconstruct the rest).
ASKED-AS: jpeg mp3 quality blurry artefacts saving again enhance zoom original photo crisp lost

ESSENCE: noticing that something is wrong is cheap; knowing which
  part is wrong costs far more — detection needs a little extra,
  correction needs enough extra to point at the culprit, and the
  choice between them is decided by whether you can ask again.
ROOT: computing (19) / repair is prepaid with redundancy — this
  floor prices the two grades of prepayment separately.
CANNOT: no correction on detection's budget. And no code correcting
  beyond the number of errors it was built for — past its bound it
  does not degrade gracefully; it either gives up or, worse,
  confidently repairs the message into a different valid one.
THREAD: conversation (a puzzled look asks for a resend; a letter to
  a spacecraft cannot), spelling (context repairs a typo),
  accounting (a trial balance detects; only the ledger corrects).
ASKED-AS: corrupted file resend download again cd scratched space probe repair detect wrong which

ESSENCE: a checksum is a short summary computed from the whole, so
  that any change shows as a mismatch — it does not protect the
  data, guard it, or vouch for it; it only reports that what
  arrived is not what left.
ROOT: mathematics / a small summary of a large thing is a
  fingerprint — and fingerprints identify without describing.
CANNOT: no checksum catching every change — a short summary of a
  long file must give the same answer for some different files, so
  some corruptions pass unseen. And no repair from it: it says
  "wrong", never "here" and never "this is what it should be".
THREAD: shipping (a manifest count catching a missing crate),
  language (a rhyme scheme that reveals a dropped line), banking
  (the last digit of an account number, checking the others).
ASKED-AS: checksum verify download hash matched corrupted file integrity sum digits card number typo

ESSENCE: redundancy buys reliability only when the copies fail
  independently — two disks from one batch, in one rack, on one
  power supply, in one building, are one disk that cost twice as
  much.
ROOT: chance (35) / multiplying odds requires independence, and
  independence is a claim about the world.
CANNOT: no reliability from copies that share a failure — the fire,
  the flood, the bad batch, the one careless command, and the
  single administrator are each a shared cause, and each turns a
  set of copies back into one.
THREAD: aviation (spare systems that share a fuel feed), farming
  (one variety planted everywhere is one plant), money (a portfolio
  of things that all fall together).
ASKED-AS: two copies same drawer both died fire flood raid disks backup separate places independent

ESSENCE: encryption does not make reading impossible, it makes it
  expensive — so every claim of security is really a claim about a
  budget and a clock: this costs more to break than the secret is
  worth, for longer than the secret matters.
ROOT: computing (19) / the one-way door — this floor states the
  door's real terms, which are money and time rather than
  impossibility.
CANNOT: no secret kept by a small key forever — everything but a
  key as long as the message, used once, falls to enough
  computation eventually, so a secret needing fifty years needs a
  far larger margin than tomorrow's password, and an enemy can
  simply store today's traffic until the machines improve.
THREAD: locks (rated in minutes against a given tool), money (a
  vault is bought by delay, not by refusal), war (a code that only
  had to hold until the battle was over).
ASKED-AS: encryption strong breakable quantum computers years cracked secure enough time cost secret worth

ESSENCE: secrecy must live in the key, not in the design — assume
  the method is published, because sooner or later it is, and the
  difference is that a key can be replaced in a second while a
  design cannot be replaced at all once it is in a million devices.
ROOT: security is a budget (this file) — a defence must be costed
  against an opponent who knows how it works.
CANNOT: no security in a method you could not afford to have
  printed. And no un-leaking a design: a secret method is a secret
  shared with everyone who ever built, sold, serviced or reverse-
  engineered the thing, which is a crowd, not a confidence.
THREAD: locks (a lock's design is public; its key is not), law (a
  published rule that still binds), war (the code book replaced
  daily while the machine stays the same).
ASKED-AS: how it works secret algorithm published open source hidden method key change locks design

ESSENCE: the two-part lock is the trick that let strangers keep
  secrets — a lock anyone may snap shut and only one held key
  opens, so a message can be sealed by someone who never met the
  recipient and holds nothing worth stealing.
ROOT: computing (19) / the one-way door — two halves built so that
  one direction is easy and the other hopeless.
CANNOT: no trust bootstrapped from nothing — the trick removes the
  need to deliver a key and leaves the need to know whose lock this
  is, so somewhere a fact must be known in advance or checked by
  another route; against someone sitting in the middle from the
  first message, mathematics alone cannot help.
THREAD: law (a notary exists for exactly this gap), introductions
  (a stranger vouched for by someone already known), passports.
ASKED-AS: https padlock browser certificate public key private secure website stranger send secret meet

ESSENCE: run the two-part lock backwards and it proves origin
  instead of hiding content — sealed with the private half, checked
  by anyone with the public half, and bound so tightly to the exact
  document that changing one letter breaks it.
ROOT: the two-part lock (this file) — the same asymmetry read in
  the other direction.
CANNOT: no lifting a signature onto another document, unlike an ink
  one. But also no signature outliving the secrecy of its key: a
  leaked key retroactively voids everything it ever signed, since
  a genuine old signature and a fresh forgery become indist-
  inguishable in the same instant.
THREAD: law (a seal binding a specific text), money (an
  endorsement), history (a document authenticated long after every
  witness is dead).
ASKED-AS: digital signature signed document verify proof sender forged tampered altered contract email valid

ESSENCE: a hash squeezes anything to a short fixed tag — the same
  input always giving the same tag, the tag giving nothing back —
  so you can check, compare and chain things without ever holding
  the things themselves.
ROOT: mathematics / a one-way function — cheap forward, hopeless
  backward.
CANNOT: no reversing a hash, and no protection for a guessable
  input either — an attacker hashes guesses as fast as you hash
  truth, so hashing a common password hides nothing at all. The
  one-way door protects the unpredictable and abandons the
  ordinary.
THREAD: fingerprints (identify without describing), libraries (a
  catalogue number standing for a book), money (a ledger whose
  entries chain by these tags so no page can be quietly changed).
ASKED-AS: password stored hashed database leaked cracked fingerprint file same tag compare check

ESSENCE: an attacker guesses at machine speed, so what matters is
  how many possible passwords there are — and length multiplies
  that count far faster than mixing in symbols; four random common
  words beat a short clever one comfortably.
ROOT: chance (35) / each added character multiplies the search, and
  multiplication outruns any amount of cunning.
CANNOT: no strength in anything a machine can enumerate — every
  memorable substitution is in the attacker's dictionary too, and
  the rules demanding a capital and a symbol push everyone into the
  same handful of shapes, shrinking the real space they were
  written to enlarge. And no safety in reuse: one breached site
  becomes every site.
THREAD: locks (more pins, not a cleverer notch), language (a phrase
  is easier to hold than a code), teaching (rules that produce
  compliance and defeat their own purpose).
ASKED-AS: password long short symbols capital letters passphrase manager reuse same everywhere hacked strong

ESSENCE: two factors help only if they are two different kinds of
  proof — something known, something held, something you are — so
  that one failure does not hand over both; a password plus a
  security question is one factor asked twice.
ROOT: redundancy needs independence (this file) — the same law,
  applied to proofs of identity rather than copies of data.
CANNOT: no second factor that shares the first's failure — a code
  sent to an email that the same stolen password opens adds
  nothing, and a phone that holds both the password manager and the
  code is one thing that can be lost once.
THREAD: law (two witnesses who were both told by the same person),
  banking (a card and a number), medicine (two tests that fail on
  the same underlying cause).
ASKED-AS: two factor code phone text authenticator login security question backup email stolen device

ESSENCE: the machinery is almost always stronger than the person
  operating it, so an attacker walks around the mathematics and
  goes at the operator — nobody breaks the cipher; they ask the
  person holding the key, and often the person simply tells them.
ROOT: strategy (23) / an opponent chooses where to strike, and
  chooses the cheapest way in.
CANNOT: no system secured above its operators — money spent
  hardening a part already stronger than the humans beside it buys
  nothing at all, so the real question is never how good the lock
  is but where the cheapest path currently runs.
THREAD: war (the bribed gatekeeper beats the wall), theatre (a
  confidence trick is this, older than any computer), engineering
  (a chain failing at its weakest link, but with the link chosen by
  an intelligence).
ASKED-AS: hacked how phone call pretending helpdesk staff clicked told them password human weakest

ESSENCE: phishing does not break trust, it borrows it — a logo, a
  familiar address, a manager's name, an invoice you were expecting
  — and the manufactured hurry exists to stop you checking, which
  makes the shape of the message a better clue than its content.
ROOT: persuasion (22) / authority and scarcity move people — this
  is that lever, aimed and automated.
CANNOT: no message proving its own origin from inside itself — any
  mark that can be seen can be copied, so verification has to
  happen through a channel the sender did not choose: a number you
  already had, a person you call back.
THREAD: money (every confidence trick, unchanged in structure for
  centuries), medicine (a fake prescription), the mind (urgency
  suppressing the slow checking part on purpose).
ASKED-AS: phishing email link click urgent boss invoice fake bank text scam verify call

ESSENCE: an untested backup is a belief, not a backup — and the
  belief is examined for the first time on the worst day, when
  nothing can be done about the answer.
ROOT: evidence (36) / a claim untested is a claim unmade — a
  backup's claim is about restoring, and only restoring tests it.
CANNOT: no proof from a successful write — a job reporting success
  has proven that writing happened, never that reading back will,
  and the ways a restore fails are not the ways a backup fails:
  missing key, unreadable format, half a database, or a folder
  quietly excluded two years ago.
THREAD: fire drills (the alarm tested, the evacuation never), the
  body (a spare tyre nobody has checked), engineering (a standby
  generator that has never been asked to carry the load).
ASKED-AS: backup restore test never tried failed drive recover files worked assumed cloud sync

ESSENCE: three copies, on two kinds of medium, one of them
  elsewhere and one of them unplugged — because each clause answers
  a different named enemy: a dead disk, a bad batch, a burnt
  building, and an attacker or a mistake that reaches everything
  connected.
ROOT: redundancy needs independence (this file) — each clause is a
  different shared cause being cut.
CANNOT: no backup in a mirror — anything that copies changes
  instantly copies the deletion instantly, so a synchronised folder
  is a convenience and not a backup. And no defence against
  ransomware in any copy the machine can still write to.
THREAD: farming (seed kept in more than one barn), archives (the
  same rule, older), money (assets held in more than one
  institution and one country).
ASKED-AS: three copies backup rule offsite cloud external drive unplugged ransomware deleted synced dropbox

ESSENCE: the medium usually outlives the machine that reads it —
  the tape is perfectly good and the drive, the cable, the card and
  the operating system that spoke to it are all gone, along with
  everyone who knew how.
ROOT: keeping knowledge (40) / formats die — this floor points at
  the other half of the chain, which is hardware and the skills
  around it.
CANNOT: no readable archive without a living reader — data nobody
  can open is indistinguishable from data deleted, and the
  difference between the two is only ever a hope. And no rescuing
  it later cheaply: the moment to copy forward is while the reader
  still runs.
THREAD: museums (film that survives and projectors that do not),
  language (a script with no living speaker), craft (a technique
  lost when its last practitioner dies).
ASKED-AS: old files floppy disk tape zip drive cant open computer gone read format hardware

ESSENCE: a format's life expectancy is the number of independent
  people who can build a reader for it — not its cleverness, not
  its owner's size — so plain, documented, widely implemented
  formats survive and elegant proprietary ones die with their
  companies.
ROOT: keeping knowledge (40) / a code with no reader is decoration
  — this floor says what keeps readers alive: many hands.
CANNOT: no format outliving its last independent implementation.
  And no proprietary format safer than the firm that owns it, so a
  company's promise of lasting support is worth exactly that
  company's own lifespan and no more.
THREAD: language (a tongue lives by its speakers' number, not its
  beauty), law (a contract in a dead language), engineering (a part
  with one supplier).
ASKED-AS: file format open standard pdf proprietary software company gone convert export locked in

ESSENCE: a name is not what identifies you — behaviour is; a
  handful of ordinary facts, or a pattern of places, times, words
  and clicks, picks one person out of millions, so removing names
  from a rich record does not make it anonymous.
ROOT: information is surprise (19) — a combination of merely
  uncommon traits is very rare, and rare means identifying.
CANNOT: no anonymity in a detailed record of a distinctive life —
  stripped datasets have been re-identified again and again by
  matching them against any other list, and the only real defences
  are coarsening the data or not collecting it.
THREAD: tracking (a walk, a typing rhythm, a phone's set of nearby
  networks), forensics (a habit convicting where no name appears),
  writing (an anonymous author found by their own style).
ASKED-AS: anonymous data names removed identified tracked privacy dataset research re identify unique pattern

ESSENCE: who spoke to whom, when, for how long, and from where
  often tells more than what was said — and it comes already
  sorted, countable and searchable, while the words themselves do
  not.
ROOT: information is surprise (19) — a pattern of contacts is
  structured, and structure is what machines can act on.
CANNOT: no delivery without addressing — a message can hide what it
  says and never entirely that it was sent, when, and to whom,
  because that part is what the road itself requires to carry it. A
  call to a clinic at three in the morning needs no transcript.
THREAD: post (an envelope's outside is public by necessity), war
  (traffic analysis reading an enemy's plans from volumes alone),
  accounting (the pattern of payments over their descriptions).
ASKED-AS: metadata who called when location phone records encrypted messages still shows contacts pattern

ESSENCE: secrecy is nobody knowing; privacy is you deciding who
  knows what, and when — so the person with nothing to hide still
  shuts the bathroom door, and information moved out of the setting
  it was given in does harm without a word of it being false.
ROOT: people together (21) / we hold different faces for different
  rooms, and that is not deception but function.
CANNOT: no privacy without a real ability to withhold, and no
  consent to a disclosure already made — you cannot agree
  afterwards to something that has already happened, which is why
  the moment of collection is the only moment where choice exists.
THREAD: medicine (a doctor holding what a colleague may not), law
  (context is the whole of confidentiality), family (a truth told
  to the wrong relative).
ASKED-AS: nothing to hide privacy secret curtains sharing who sees context employer family doctor

ESSENCE: nobody can be held to account for what was not recorded,
  so accountability is bought with logs — and a log is only
  evidence if the person it describes cannot edit it, which means
  it has to leave the machine that makes it, immediately.
ROOT: accounting (70) / a trail nobody can quietly change — this
  floor names the mechanism: distance from the actor.
CANNOT: no accountability from a log its subject can rewrite — an
  intruder's first act is the log, and an administrator with power
  over the record has power over the past. And no free
  accountability: every log is also a surveillance record of the
  ordinary people it watches, kept forever unless someone decides
  otherwise.
THREAD: law (evidence held by a neutral party), sport (a referee
  who is not on either team), history (a chronicle written by the
  king it praises).
ASKED-AS: logs audit who did it deleted covered tracks record admin history server monitoring

ESSENCE: grant access to jobs, not to people — a role can be
  argued about, reviewed, and handed over, while a list of
  individual exceptions cannot be understood by anyone six months
  later, including whoever wrote it.
ROOT: law (17) / a rule stated generally can be examined; a
  thousand particular favours cannot.
CANNOT: no review of a permission that was never justified — and no
  list staying correct without removal, since access is added by
  need and taken away by nobody, so people who change jobs
  accumulate the powers of every job they have held.
THREAD: keys (a building's master key list, and how it rots),
  accounting (segregation of duties depends on roles being real),
  organisations (an old title carrying an old authority).
ASKED-AS: permissions access rights groups role job leaver still has account old employee removed review

ESSENCE: give every account and every program the least it needs,
  because each permission is also a permission for whoever takes
  the account over — the point is not to prevent the break-in but
  to decide in advance how far it can walk.
ROOT: strategy (23) / plan for the breach, not only against it —
  containment is a separate discipline from prevention.
CANNOT: no containing a breach of an all-powerful account — once it
  is taken there is nothing left to bound, so the damage is decided
  by a choice made long before, when the account was given powers
  it did not need for its daily work.
THREAD: ships (watertight compartments: the hull will be holed),
  fire (doors that hold a building's fire to one wing), banking
  (a teller's till limit).
ASKED-AS: admin rights account permissions minimum needed limited damage spread ransomware whole network compromised

ESSENCE: an intelligent opponent picks where to enter, so the
  average standard of a system is irrelevant and the worst-kept
  part is the whole story — the forgotten test server, the printer
  nobody patches, the contractor's account still live.
ROOT: engineering (04) / a system fails at its weakest point — with
  the difference that here the weak point is deliberately searched
  for rather than merely encountered.
CANNOT: no defending an asset you do not know you own, so an
  inventory comes before any defence; and no security score that is
  an average, since one open door makes the other hundred locked
  ones decorative.
THREAD: fortification (the postern gate, in every siege), medicine
  (an infection entering by the one break in the skin), audit (the
  account nobody has looked at in years).
ASKED-AS: old server forgotten unpatched printer test system contractor account weakest point inventory assets breach

ESSENCE: keys are made of randomness, so unpredictability is the
  raw material of the whole field — and real randomness is hard for
  a machine, since a machine is a device for doing the same thing
  every time.
ROOT: mathematics / a key's strength is the size of the space it
  was drawn from, and a predictable draw shrinks that space to one.
CANNOT: no secret from a predictable source — most real breaks of
  strong systems have come this way, from a clock used as a seed,
  a repeated value, or a generator that shipped with the same
  starting point in every device. The mathematics was never
  touched; the dice were loaded.
THREAD: gambling (a rigged shuffle beats any strategy), war (a
  cipher clerk who reused a setting), chance (people cannot produce
  a random sequence by trying).
ASKED-AS: random numbers generator seed predictable dice shuffle keys guessed same every device weak

ESSENCE: since attackers guess by the billion, the defence is to
  make each guess slow and each user's stored secret different —
  add a unique scrap to every password before hashing, and choose a
  hash built to be deliberately expensive.
ROOT: hashing is one-way (this file) — this floor takes the two
  known holes in it and closes each with a matching trick.
CANNOT: no cracking a whole stolen database at once when every
  entry is salted differently — the attacker must attack each in
  turn, and a hash tuned to take a tenth of a second turns weeks of
  guessing into centuries. The defence buys nothing for the
  strongest password and everything for the ordinary one.
THREAD: locks (a delay built into a safe dial), post (a queue that
  slows a flood without stopping a customer), farming (varied crops
  so one pest cannot take the field in one pass).
ASKED-AS: password database leaked hashed salt slow bcrypt cracked millions guesses per second protect

ESSENCE: bounding the number of attempts is cheaper than bounding
  the strength of the secret — a four-digit code is trivial to
  guess and perfectly safe behind three tries and a lockout, which
  is why a bank card works at all.
ROOT: security is a budget (this file) — the attacker's cost can be
  raised on either side of the equation, and one side is far
  cheaper to buy.
CANNOT: no offline rate limit — the trick works only while the
  guessing must go through your door, so the moment an attacker
  holds a copy of the data they can guess at their own machine's
  speed with no counter to stop them. Which side of the door the
  secret sits on changes everything about how strong it must be.
THREAD: exams (limited attempts), law (a statute of limitations
  bounding exposure by time), games (a life count changing how a
  puzzle must be solved).
ASKED-AS: pin four digits card locked out three attempts safe bank guess tries limit blocked

ESSENCE: you run other people's code — libraries, updates, firmware
  and services — so your security is the security of everyone whose
  work you trust, and their suppliers, and theirs.
ROOT: software (61) / a program stands on programs written by
  strangers — this floor adds that the strangers are also targets.
CANNOT: no trusting a program without trusting its whole tree — an
  attacker who cannot reach you can reach something you install
  automatically, which turns one break into thousands. And no
  auditing your way out: nobody reads the whole tree, and the tree
  changes weekly.
THREAD: food (a contaminated ingredient recalled across a hundred
  brands), manufacturing (one faulty component in every model),
  finance (a counterparty's counterparty).
ASKED-AS: update supply chain library dependency package compromised vendor software installed automatically trusted third party

ESSENCE: build as though each layer will fail, because one of them
  will — a wall, then a lock, then an alarm, then a limit on what
  the intruder can reach, so that no single mistake is the whole
  story.
ROOT: least privilege (this file) — the same instinct, generalised
  from accounts to the whole shape of a system.
CANNOT: no perfect layer, and so no design that rests on one — the
  common catastrophe is not a weak defence but a single strong one
  trusted absolutely, with nothing behind it because nothing was
  thought to be needed.
THREAD: ships (hull, bulkhead, pump, lifeboat), medicine (skin,
  then immune system, then treatment), aviation (checklists,
  redundancy, training, and a recorder for when all three fail).
ASKED-AS: layers firewall antivirus backup alarm one thing failed still protected defence depth assumed

ESSENCE: since not everything can be prevented, the number that
  matters is how long an intruder goes unnoticed — the difference
  between a break found in an hour and one found in eight months is
  the difference between an incident and a catastrophe.
ROOT: strategy (23) / plan for the breach — once the break is
  assumed, the measurable quantity is time, not certainty.
CANNOT: no prevention-only defence — a system with no way to notice
  cannot tell a quiet year from a compromised one, and absence of
  alarms is not evidence of safety when nothing is listening.
THREAD: medicine (screening: the cancer's danger is mostly how late
  it is found), farming (a pest caught in one row or in the field),
  accounting (a fraud's size grows with the months before discovery).
ASKED-AS: detected months later breach discovered how long noticed alarm monitoring intruder inside quietly stealing

ESSENCE: deleting removes the label, not the content — the file
  system forgets where the thing was and the bytes stay until
  something happens to write over them, and meanwhile the same data
  sits in backups, caches, search indexes, logs and someone's
  screenshot.
ROOT: computing (19) / copying is free and perfect — anything that
  copies easily has already copied more times than anyone tracked.
CANNOT: no un-sharing and no reliable deleting of a thing that has
  travelled — a promise to erase can only cover the copies its
  maker knows about, and nobody knows about all of them, which is
  why the only certain control over data is at the moment it is
  collected.
THREAD: paper (a shredded document rebuilt; a photocopy in a
  drawer), law (a right to be forgotten meeting this fact),
  gossip (a retraction reaching fewer ears than the rumour).
ASKED-AS: deleted file recover recycle bin gone forever wiped drive backups copies internet screenshot erase

ESSENCE: data kept is data that can be stolen, subpoenaed, leaked
  or misused, so every record has a running cost in risk — the
  safest record is the one never made, and the second safest is the
  one already destroyed on schedule.
ROOT: deletion is hard (this file) — since removal is unreliable,
  the decision that matters is whether to collect at all.
CANNOT: no losing what was never held. And no keeping without
  exposure: a store held "just in case" is a liability accruing
  quietly, and the case it is kept for is nearly always rarer than
  the breach it enables.
THREAD: accounting (retention schedules exist for this reason),
  keeping knowledge (40) (forgetting as a feature, here for a
  different reason), law (discovery reaching everything kept).
ASKED-AS: keep data forever storage cheap delete old records retention breach leaked collected why kept

ESSENCE: harmless facts combine into a harmful one — a postcode, a
  birthday and a job title are each public and together they are a
  person; a year of ordinary locations is a life.
ROOT: behaviour identifies (this file) — the identifying power is
  in the combination, so it cannot be found by examining fields one
  at a time.
CANNOT: no assessing risk field by field — every review that asks
  "is this item sensitive?" will pass a dataset that is dangerous
  as a whole, which is why the question has to be asked of the join
  and not of the column.
THREAD: intelligence work (a picture assembled from unclassified
  scraps), medicine (symptoms harmless alone), evidence (a case
  built of individually weak facts).
ASKED-AS: combined data pieces harmless together identify profile birthday postcode job location year picture

ESSENCE: a system that is unusable is also failing — locked-out
  staff, lost work and stalled emergencies are real harms, and
  security so heavy that people route around it has made the system
  less safe, not more.
ROOT: people together (21) / rules that obstruct the work get
  quietly replaced by whatever gets the work done.
CANNOT: no security that ignores the people using it — the shared
  password on a sticky note, the personal email used to move a
  file, and the disabled scanner are not indiscipline; they are the
  predictable output of a control that made the job impossible.
THREAD: medicine (an alarm that sounds so often it is muted), law
  (a rule too strict to enforce, enforced arbitrarily), safety
  (a guard removed because the machine could not be used with it).
ASKED-AS: too strict locked out password reset annoying workaround sticky note bypass staff usable rules

ESSENCE: being read is often the smaller harm — a record silently
  changed is worse, because everything afterwards is decided on it
  and nobody knows to doubt it.
ROOT: accounting (70) / a system of record is only worth its
  integrity — a false entry propagates while a copied one merely
  escapes.
CANNOT: no correcting what was never noticed as wrong — a changed
  number carries no mark of its change, so the defence must be
  built beforehand as signatures, chained hashes or an off-machine
  copy to compare against. Afterwards there is nothing to compare.
THREAD: history (a forged charter accepted for centuries),
  medicine (a wrong blood type in a file), navigation (a chart with
  a rock removed).
ASKED-AS: changed record altered data tampered wrong number nobody noticed trust database edited quietly integrity

ESSENCE: a cipher is trusted because many skilled people tried to
  break it and failed in public over years — not because it was
  proved safe, since almost none are, and not because it is
  secret.
ROOT: evidence (36) / one result is a rumour — a design becomes
  knowledge only when strangers with their own hands attack it.
CANNOT: no confidence in a scheme nobody has attacked — so a
  home-made cipher, however ingenious, is untested by definition,
  and "we invented our own" is the reliable sign of a system about
  to fail. Newness is a liability here, uniquely among fields.
THREAD: medicine (a drug trusted after trials, not after theory),
  engineering (a design proven by service years), science
  (replication as the only credential).
ASKED-AS: own encryption invented custom algorithm standard tested years experts broken trust proven roll

ESSENCE: a key must be cancellable, and cancelling it is the hard
  half — the message that it is no longer good has to reach every
  place that might check it, and reach them before the thief does.
ROOT: signatures prove origin (this file) — the proof rests on the
  key still being the right one, which is a fact that can change.
CANNOT: no revocation faster than the slowest verifier — anything
  offline, cached, or built to keep working without a network
  cannot be told, so a scheme's real security is the window between
  losing a key and the last checker learning of it.
THREAD: banking (a stolen card and the hours before every terminal
  knows), law (a repealed rule still applied by someone with an
  old book), keys (a master key lost and every lock to change).
ASKED-AS: revoke certificate expired stolen key cancel card lost still works offline check update window

ESSENCE: if someone can touch the machine, the software argument is
  over — they can boot their own, read the disk directly, attach to
  the memory, or simply carry it away, and no permission written in
  software survives that.
ROOT: computing (19) / no bit without a body — every protection is
  ultimately a physical arrangement, and physical arrangements
  yield to physical access.
CANNOT: no software defence against physical possession — full-disk
  encryption raises the price and even that gives way if the
  machine was taken while running, with the key still sitting in
  its memory.
THREAD: banking (the vault door is real, not a policy), war (a
  captured cipher machine ends a system), the body (any
  argument ends when the door is broken).
ASKED-AS: stolen laptop encrypted disk locked screen someone took machine access physical server room theft

ESSENCE: a secret's life expectancy falls with the number who hold
  it — every additional holder is another chance of a slip, a
  grudge, a device left on a train — so the count of people who
  know is itself a security number worth tracking.
ROOT: computing (19) / a secret told is a copy made, and copies
  cannot be recalled.
CANNOT: no secret kept by many — armies and governments learn this
  every generation, and the arithmetic does not care about loyalty
  or clearance levels, only about the number of independent chances
  for it to leave.
THREAD: medicine (a diagnosis shared through a family), business
  (a merger leaking as the circle widens), history (conspiracies
  large enough to be certain of exposure).
ASKED-AS: who knows secret told few people leak spread more chance kept quiet team circle

ESSENCE: most losses are not clever attacks but ordinary mistakes —
  a database left open to the internet, an email sent to the wrong
  list, a shared folder set to public, a backup on a lost drive.
ROOT: engineering (04) / no part is made exact — a default left
  unchanged is a decision made by whoever wrote the default.
CANNOT: no defence built only against the clever — a programme that
  models a determined opponent and ignores the tired administrator
  on a Friday afternoon has aimed at the rarer threat, and the
  cheapest security work available is nearly always making the safe
  setting the default one.
THREAD: aviation (checklists exist because skill is not the failure
  mode), medicine (wrong-site surgery prevented by a marker pen),
  driving (most crashes are ordinary lapses, not racing).
ASKED-AS: misconfigured public bucket wrong email sent everyone default settings mistake exposed accident leak simple

ESSENCE: hiding that a message exists is a different problem from
  hiding what it says, and often the harder one — an unbreakable
  cipher still announces that two people are talking, which in some
  circumstances is the only fact that matters.
ROOT: metadata reveals more than content (this file) — this is the
  same truth stated as a design goal rather than a leak.
CANNOT: no concealing a message without concealing its traffic —
  and concealment of traffic costs real waste: constant dummy
  messages, padding to fixed sizes, and routes taken through
  strangers, because a channel that is quiet when nothing is
  happening has already spoken.
THREAD: war (radio silence itself being a signal), smuggling (an
  ordinary-looking cargo beats a locked one), the mind (a person
  refusing to answer has answered).
ASKED-AS: hidden message secret exists talking someone noticed silence signal disguise cover innocent looking traffic

ESSENCE: publishing a fix is publishing the flaw — the patch shows
  attackers exactly where the hole was, so the clock on every
  unpatched machine starts at the moment of the announcement, and
  it runs in hours.
ROOT: information is surprise (19) — a fix is a message about a
  weakness, and it is legible to everyone who receives it.
CANNOT: no quiet patching at scale — a fix cannot be shipped to
  defenders without also being shipped to anyone who cares to read
  it, so there is no arrangement in which the defender gets a long
  head start. The only variable left is how fast the update lands.
THREAD: medicine (announcing a vulnerability in a drug supply),
  law (a loophole published in the ruling that closed it),
  war (a countermeasure revealing what it counters).
ASKED-AS: update now patch security fix urgent released exploit attackers reverse engineer old version vulnerable
