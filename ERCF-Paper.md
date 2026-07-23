# The Evacuation Risk and Cost Framework (ERCF)

### A Research Report on a Decision-Support Tool for Estimating the Human and Financial Cost of Civilian Evacuation in Armed Conflict

*Prepared as a plain-language review of the ERCF research prototype*
*based on the software and documentation contained in this repository*

---

## Foreword

A humanitarian organisation facing a besieged city has to answer a question that no
manual answers well: what would it actually take to move these people, and what
would it cost to keep them alive if they cannot be moved? The first question is
about buses, fuel, drivers, water, tents and escorts. The second is about convoys
that have to reach a place where fighting is still going on, and about how much of
what is loaded onto those convoys will never arrive. Both questions have to be
answered before a funding appeal can be written, and both are usually answered from
memory, from a previous operation in a different country, or from an experienced
coordinator's intuition.

The Evacuation Risk and Cost Framework, known as ERCF, is a research prototype that
attempts to put numbers on both questions and to show its working. It is a piece of
software that a planner uses through an ordinary web browser. The planner describes
a situation by moving seven sliders, entering a population figure and a distance,
and the tool returns an itemised cost estimate for evacuating that population, a
separate itemised cost for assisting them where they are, and an estimate of how
many days would pass before the second becomes more expensive than the first.

This report explains what ERCF measures, what every one of its inputs and internal
numbers represents, where those numbers came from, how confident their author is in
each of them, and what the tool cannot do. It is written for a policy, humanitarian
and legal readership rather than a technical one. No prior knowledge of software is
assumed.

---

## 1. Executive Summary

1.1 ERCF is a research prototype: experimental software, not an operational system.
It helps a humanitarian planner estimate two things side by side. The first is the
one-time cost of organising an evacuation. The second is the daily cost of keeping
people supplied if they stay. It then compares the two.

1.2 The planner describes the situation using seven factors, called dimensions and
labelled D1 to D7. Each is scored from 1 to 5. They cover the intensity of fighting,
the mobility of the population, whether the armed parties have authorised movement,
the state of roads and logistics, the safety of the destination, how fast the window
is closing, and how good the available information is. These seven scores drive
everything else the tool produces.

1.3 The seven scores are combined into a single weighted number, which is placed in
one of five risk levels from Level 0 to Level 4. That level then selects the cost
rates, loss rates and mortality rates used in the rest of the calculation. A
planner who moves one slider sees the entire cost estimate change.

1.4 The distinctive output is the break-even analysis. Evacuation is a large
one-time expense. Assistance in place is a smaller expense repeated every day.
Somewhere in the future, if the crisis persists, the cumulative daily cost overtakes
the one-time cost. ERCF calculates the day on which that happens, which is a
question funding appeals have to answer and rarely answer with arithmetic.

1.5 ERCF also produces an estimate of deaths and injuries among a population that
does not leave. This estimate was fitted against sixteen documented historical
conflicts. Its author is explicit that this part of the tool is indicative and that
the financial estimates are considerably more reliable than the mortality ones.

1.6 The project takes an explicit ethical position, stated in its own documentation
and repeated in the interface. It estimates the cost of logistics. It does not place
a monetary value on human life, and it does not tell a user whether an evacuation is
worth carrying out. The labels it produces are descriptive, not instructions.

1.7 The software is substantially built rather than aspirational. The repository
contains roughly eleven thousand lines of working Python, a browser interface, a
reproducible calibration pipeline, a database of thirty-one documented historical
conflicts, and connections to four external data services. It runs as a live public
demonstration. What remains incomplete is documented openly in the project's own
backlog and is discussed in Section 16 of this report.

---

## 2. Background and Rationale

2.1 The problem. An organisation deciding whether to support an evacuation needs
three figures quickly: what evacuation would cost, what staying would cost, and
where those two lines cross. Each figure exists somewhere. Sphere standards give
water and food quantities per person. The World Food Programme publishes what its
air service costs per passenger kilometre. Case studies record what particular
operations spent. But these sit in separate documents written for separate purposes,
and nobody has assembled them into a single calculation that a planner can run in an
afternoon.

2.2 The gap. The project's concept document states the position directly: these
estimates exist in operational manuals and case studies, but no publicly available
tool integrates them with a historical calibration dataset and a framework grounded
in International Humanitarian Law. ERCF is an attempt to build that integration and
to publish the assumptions rather than hide them.

2.3 A gap in the published literature. One finding recorded in the source code is
worth restating for a policy audience. When the author searched for a published
figure describing how much more expensive it is to deliver humanitarian assistance
inside an active conflict than in a stable setting, no such figure was found. The
International Federation of Red Cross and Red Crescent Societies confirms in a 2021
methodology paper that the per-capita cost of response is statistically
significantly higher in conflict, but publishes no ratio. The World Food Programme
publishes per-tonne logistics costs that imply a premium of roughly 1.23 times for
Sudan in 2023 against an Eastern Africa regional average. Security costs, which the
model treats as the larger component, appear only in fragments: an armed escort in
Yemen at up to 3,000 US dollars per convoy on one route, security spending in
Somalia in 2017 estimated at around 400 million US dollars per year against total
humanitarian operations of 700 to 900 million. The code notes that a single
published multiplier for active-conflict delivery does not appear to exist, and that
this model may be among the first attempts to quantify it explicitly. That is an
honest statement of a weakness and of a contribution at the same time.

2.4 The response. ERCF builds the calculation anyway, using the best documented
values available, and tags every single number with the strength of the evidence
behind it. A planner reading the interface can see which figures are validated
against a published standard, which are estimated from indirect evidence, and which
are unvalidated assumptions the author could not support from any public source.
That tagging is the tool's principal safeguard against being trusted more than it
deserves.

---

## 3. Objectives

The tool is designed to:

3.1 Produce a rapid, itemised cost estimate for a civilian evacuation operation,
broken into transport, fuel, personnel, food, water, shelter, medical supplies,
communications and contingency.

3.2 Produce a parallel estimate for the cost of assisting a population that remains
in the conflict zone, including the extra cost that conflict access conditions
impose and the proportion of supplies that never arrives.

3.3 Identify the break-even point at which continuing in-zone assistance becomes
more expensive than a one-time evacuation, so that funding appeals can be argued
from arithmetic rather than assertion.

3.4 Place the current situation against documented historical operations, so that a
planner can see which past conflicts a scenario most resembles.

3.5 Make every parameter, source and confidence level visible in the interface
rather than buried in the code.

3.6 Keep the estimate of financial cost separate from the estimate of mortality, so
that a funding calculation is never confused with a casualty prediction.

---

## 4. How ERCF Works: The Seven Dimensions

The whole tool rests on seven scores. Each is a number from 1 to 5 that the planner
sets by moving a slider. The dimensions were chosen, according to the concept
document, to capture the factors that field coordinators consistently cite when
assessing whether an evacuation is feasible, and deliberately to require no
real-time data feed or classified intelligence. A planner with a situation report
and professional judgment can set all seven.

4.1 D1, Kinetic Threat. How much direct violence the civilian population is exposed
to. A score of 5 means active, sustained attack. This is the dimension that drives
almost everything downstream: it determines whether movement is physically survivable
at all.

4.2 D2, Mobility Constraints, also called Vulnerability. How much of the population
cannot move unaided. A high score means many people who are elderly, very young,
disabled, chronically ill or otherwise dependent on assisted transport. This
dimension is what forces the operation to allocate medical buses and ambulances
rather than ordinary buses.

4.3 D3, Authorization. Whether the armed parties have consented to civilian
movement. Note carefully that the scale runs the same direction as the others: a
high D3 score means authorization is a serious problem, that is, that consent is
absent or unreliable. Without consent, an evacuation is both unlawful and
practically blocked.

4.4 D4, Logistics. The state of roads, bridges, vehicles, fuel supply and the
supporting infrastructure. The project's documentation observes that logistics
collapse, not danger as such, has empirically been the leading cause of delayed
evacuations, citing Mosul in 2016 and Aleppo in 2016.

4.5 D5, Destination. Whether the place people would be moved to is genuinely safe
and able to receive them. The reason this dimension exists at all is Srebrenica in
1995, cited in the code as the canonical case in which evacuation to a nominally
safe area became the site of a massacre. Moving civilians into danger is a distinct
harm, not a lesser version of leaving them where they are.

4.6 D6, Urgency. How fast the window for organised movement is closing.

4.7 D7, Information. How poor the information environment is. A high score means
communications failure, rumour, and an inability to coordinate.

### 4.8 The weights, and why they are what they are

The seven scores are combined into a single number by multiplying each by a weight
and adding the results:

    risk score = D1×0.25 + D2×0.15 + D3×0.15 + D4×0.15 + D5×0.15 + D6×0.10 + D7×0.05

The weights add up to 1.00, so the resulting score stays on the same 1 to 5 scale as
the inputs. The reasoning recorded in the source code for each weight is as follows.

D1 carries the largest weight, one quarter of the total, because direct physical
threat is treated as the primary driver of evacuation necessity, and because it is
the dimension that alone determines whether movement is safe. It is tied to the
precautionary obligations in Articles 57 and 58 of Additional Protocol I.

D2, D3, D4 and D5 each carry fifteen per cent and form an equal group. The argument
is that mobility, consent, logistics and destination safety are each individually
capable of making an evacuation impossible, so none should dominate the others. D3
is explicitly capped at fifteen per cent rather than being set higher, because the
most extreme authorization failures are already captured elsewhere in the tool by
the hard trigger described below.

D6 carries ten per cent, deliberately below the equal group. The reasoning is that
urgency is largely absorbed by D1 in the most extreme situations, and that the tool
captures urgency more sharply through the hard trigger and through a separate
extraction-probability floor than a linear weight would.

D7 carries five per cent, the lowest. Poor information raises coordination cost and
panic risk, but on its own it does not determine whether an evacuation is necessary
or possible.

4.9 An important caveat, stated by the author in the code itself and reproduced in
the interface as a red marker beside every weight: all seven weights are modelled
estimates. No published framework in International Humanitarian Law or humanitarian
operations specifies numerical weights for these factors, so there was nothing to
copy. The author's own backlog lists expert-panel validation of these weights as
outstanding research work. A reader should treat the weights as a reasoned starting
proposal, not as an established standard.

---

## 5. From Seven Scores to a Risk Level

5.1 The weighted score is placed into one of five bands, each with a label and a
NATO-doctrine equivalent used in military planning:

- Level 0, Baseline and Monitoring, score of 1.5 or below. NATO equivalent:
  permissive and stable.
- Level 1, Low Risk and Advisory, above 1.5 up to 2.5. Permissive but degrading.
- Level 2, Moderate Risk and Watchful, above 2.5 up to 3.5. Uncertain.
- Level 3, High Risk and Contested, above 3.5 up to 4.2. Hostile, partial.
- Level 4, Critical and Emergency, above 4.2. Hostile, imminent.

5.2 The hard trigger. There is one override. If D1 and D6 are both at 4.5 or above,
that is, if violence is extreme and the window is closing at the same time, the score
is floored at 4.21, which forces Level 4 regardless of how favourable the other five
dimensions look. This exists because the linear weighted average would otherwise
allow good logistics and a safe destination to pull an imminent massacre down into
Level 3.

5.3 Why the level matters so much. The level is not merely a label. It selects the
numerical rates used everywhere downstream: the security escort ratio, the daily
cost of assistance per person, the access multiplier, the supply loss rate, the
injury rate, the mortality base rate, and the probability of emergency extraction.
Almost every figure the tool produces changes when the level changes. This is a
design choice worth noticing, because it means the five-band classification carries
a great deal of weight and the boundaries between bands, at 1.5, 2.5, 3.5 and 4.2,
are themselves modelled judgments rather than empirical findings.

### 5.4 Three separate questions instead of one number

Alongside the composite score, the tool computes three sub-indexes that keep
distinct questions apart. This was added on the recommendation of the project's
academic reviewers.

Risk Severity asks how dangerous the situation is for civilians. It is built from D1,
D2 and D6 only, rescaled back onto a 1 to 5 range.

Feasibility asks whether people can realistically move. It is built from D3, D4 and
D5, but inverted: because a high D3, D4 or D5 score means bad conditions, each is
subtracted from 6 before being used, so that a high feasibility number means a
genuinely open corridor. The resulting labels run from "impossible, corridor blocked
or does not exist" through "severely constrained" and "viable with significant risk"
to "good, organised corridor with manageable risk".

Information Quality is simply 6 minus D7, so that a high number means good
situational awareness.

5.5 Keeping severity and feasibility apart matters. A situation can be extremely
dangerous and simultaneously impossible to evacuate. Blending the two into one score
would make that case look moderate, which is precisely the case that should escalate
most urgently. The tool instead places the scenario in a four-cell matrix. High
severity with high feasibility returns "evacuate immediately". High severity with
low feasibility returns "shelter in place and negotiate a corridor urgently", with
the reasoning that forced movement without a safe corridor risks greater harm than
staying, and with a note that the precautionary obligations under Articles 57 and 58
of Additional Protocol I apply while negotiation continues. Low severity with high
feasibility returns "facilitate voluntary departure" and explicitly says do not
mandate evacuation. Low severity with low feasibility returns "monitor and reassess
daily".

---

## 6. The Cost of Evacuating: Every Variable Explained

This is the part of the tool with the strongest evidentiary foundation, and it is
worth going through in full. The planner supplies four things: the population at
risk, the percentage of that population who are vulnerable, the distance in
kilometres to safety, and the terrain quality. Everything else is derived.

### 6.1 How many vehicles

The population is split into vulnerable and non-vulnerable. Non-vulnerable people
are assigned to standard buses at 50 people per bus. Vulnerable people are assigned
to medical buses at 20 people per bus, and ambulances at one per 150 vulnerable
people. The bus capacities are marked in the code as operational assumptions not
validated against field data. The ambulance ratio has a history worth recording: it
was originally set at one ambulance per 40 vulnerable people, and was revised to one
per 150 after the author found that no published field standard exists at all and
that the original figure was three to five times above what documented practice, in
particular a study of the Kosovo operation, actually showed.

The number of medical buses and ambulances is then multiplied by a factor derived
from D2, the mobility dimension. At D2 of 1 the factor is 0.8, at D2 of 2 it is 1.0,
at 3 it is 1.3, at 4 it is 1.8, and at 5 it is 2.5. In plain terms, a population
with severe mobility constraints needs roughly two and a half times the assisted
transport of a baseline population. This factor is described in the code as
estimated with no primary source.

### 6.2 How many people to run the operation

Security staff are assigned according to the risk level, and the ratio tightens
sharply as danger rises: no security at Level 0, then one security person per 500
civilians at Level 1, per 200 at Level 2, per 100 at Level 3, and per 50 at Level 4.
Medical staff are assigned at one per 250 people, which is the Sphere Handbook 2018
standard for clinical officers in emergency settings. This figure was corrected
upward during development: an earlier version used one per 500, half the Sphere
standard, with no documented justification. Paramedics are assigned at one per 100
people, and one driver per vehicle.

Daily rates are 300 US dollars for security, 200 for medical staff, 150 for
paramedics and 50 for drivers. These are total cost to the operation, not take-home
pay. All four are tagged as estimated. The code carries an unusually candid note
about them: every rate implicitly assumes national staff or a lower-cost
international non-governmental deployment at roughly the level of Médecins Sans
Frontières, and full United Nations international professional staff, once daily
subsistence allowance and danger pay are included, would cost three to six times
more. The author records that this assumption is not stated in the interface and
should be flagged.

### 6.3 Supplies

Water is calculated at 20 litres per person per day for three days. This is the
UNHCR full planning standard, chosen deliberately over the Sphere emergency minimum
of 7.5 to 15 litres because an evacuation is a planned operation rather than a
first-response emergency. Food is calculated at 0.45 kilograms of dry food per
person per day for three days, which is the dry-weight equivalent of the Sphere
minimum of 2,100 kilocalories per person per day. Tents are provided at one per five
people, which at the Sphere standard of 3.5 square metres per person gives 17.5
square metres per tent and is internally consistent. Basic medical kits are provided
at one per 100 people, and trauma kits at one per 50 people when the risk level is 3
or above, or one per 200 otherwise. Radios are provided at one per five vehicles
plus a fixed five for coordination.

### 6.4 What each of those things costs

Standard buses are costed at 200 US dollars each, medical buses at 400, and
ambulances at 700. The medical bus and ambulance figures were revised upward during
development after research found no primary source for the earlier values; the
revised figures sit at the lower bound of documented field ranges for
medically-equipped vehicles. Fuel is calculated at 0.35 litres per kilometre per
vehicle for a return journey, priced at 1.20 US dollars per litre, revised down from
1.50 on the basis of ACAPS reporting of Yemeni consumer fuel prices in 2022. Food is
priced at 3 US dollars per kilogram, a figure the project's own parameter registry
flags as having no citation behind it even though the quantity does. Water is priced
at 0.05 US dollars per litre, and here the code is unusually honest: field evidence
gathered in 2026 found real water trucking costs ranging from 2 to 23 US dollars per
cubic metre, all of which are below the model's baseline, and the author records that
the lower figures were not adopted pending further validation. Tents are priced at
380 US dollars each, raised from an earlier 150 after the earlier figure was found to
describe a tarpaulin kit suitable for a week rather than a standard tent; 380 sits
just below the 400 dollar replacement cost UNHCR gave publicly in 2022. Basic medical
kits are priced at 21 US dollars, derived from the WHO and UNICEF Interagency
Emergency Health Kit costing, revised down from an earlier 50 which was roughly seven
times too high for a three-day convoy. Trauma kits are priced at 200 US dollars and
remain unvalidated, because the ICRC does not publish per-kit pricing. Radios are
priced at 500 US dollars each, within the documented procurement range for
professional handheld VHF units.

### 6.5 Three multipliers applied on top

Terrain multiplies transport and fuel costs. The five levels run from 4.0 for the
worst terrain down to 1.0 for the best, with 2.5, 1.7 and 1.2 in between. The lower
end of this range is consistent with published road-condition cost models; the upper
end of 4.0 is an expert estimate consistent with a World Food Programme figure
showing per-tonne delivery costs in the Central African Republic, South Sudan and
the Democratic Republic of the Congo running about five times a standard country
average, though that figure mixes terrain, access and security together.

Season adjusts terrain further. If the operation starts in a month the tool
classifies as a closure period for that latitude, the terrain multiplier is boosted
by 50 per cent for the worst terrain, 30 per cent for the second worst and 20 per
cent for middling terrain. Closure periods are set by latitude: December to March
above 30 degrees north, June to September below 30 degrees south, and April to
October in the tropics for wet season. The author describes these as broad regional
approximations. The most useful output here is not the cost boost but a flag: the
worst terrain in a closure period is marked potentially impassable, which is an
operational warning rather than a number.

D4, logistics, adds 10 per cent to transport and fuel for each point above 1, so a
D4 of 5 adds 40 per cent. D5, destination, changes the number of tents needed: a
destination with good existing infrastructure halves the tent requirement, a
destination with none doubles it. Both are marked estimated with no primary source.

Finally, 15 per cent is added to the whole subtotal as contingency, which the code
justifies as the lower bound of the 15 to 20 per cent standard used for high-risk
projects.

### 6.6 A worked example, taken from the code

For 10,000 people, 20 per cent of them vulnerable, at Level 2, moving 50 kilometres:
160 standard buses, 100 medical buses and 50 ambulances, 310 vehicles in total; 50
security staff, 20 medical staff, 100 paramedics and 310 drivers; 10,850 litres of
fuel, 15,000 kilograms of food, 450,000 litres of water, 2,000 tents and 67 radios.
Transport comes to 92,500 US dollars, fuel to 16,275, personnel to 34,000, food to
45,000, water to 22,500, shelter to 300,000, medical to 15,000 and communications to
33,500, giving a subtotal of 558,775, a contingency of 83,816, and a total of roughly
643,000 US dollars, or about 64 dollars per person. Shelter dominates, which is a
useful thing for a planner to be able to see at a glance.

---

## 7. The Cost of Staying

The second calculation estimates what it costs an organisation to keep a population
alive where it is. It has three parts.

7.1 Supply delivery. The starting point is 3.50 US dollars per person per day. This
is a multi-sector figure covering food, water, health, shelter and coordination. The
World Food Programme's own global average for food and cash assistance alone was 42
US cents per beneficiary per day in 2023, and the code explains the difference
between the two figures at some length: at the full Sphere water standard, water
alone dominates supply weight, and applying the World Food Programme's per-tonne
Sudan delivery cost to that weight gives 3.28 US dollars per person per day, within
six per cent of the model's figure. That is a genuinely careful piece of reasoning.

The baseline is then multiplied by an access multiplier that represents how much more
expensive delivery becomes as conflict intensifies: 1.0 at Level 0, 1.5 at Level 1,
2.0 at Level 2, 3.6 at Level 3 and 4.0 at Level 4. These figures were revised
downward during development, from earlier values of 3.0, 5.0 and 8.0 for the top
three levels, after the author's research established that documented sources support
only about 2.5 to 3.6 times at Level 3 and nothing above about 4 times at Level 4.
Level 4 remains marked as directionally plausible but unconfirmed, and the project's
backlog lists it as the outstanding unvalidated cost parameter.

A further penalty is applied from D4, and the terrain and seasonal multipliers apply
here too, because bad roads make delivery expensive whether people are leaving or
staying.

7.2 Supplies that never arrive. A loss rate is then added, representing goods
destroyed, looted or simply undelivered: 5 per cent at Levels 0 and 1, 15 per cent at
Level 2, 30 per cent at Level 3 and 50 per cent at Level 4. Only the lowest of these
has any published anchor: OCHA monitoring of Gaza during the ceasefire period in late
2025 recorded under two per cent of cargo looted or intercepted under active
monitoring, and the model uses 5 per cent as a planning buffer including spoilage.
The three higher figures are internal planning estimates with no published equivalent
that the author could find. A high D3, meaning consent is absent, adds further to the
loss rate, and a high D7, meaning poor information, adds a coordination overhead.

7.3 Emergency extraction. The model assumes that some proportion of the population
will have to be pulled out in an emergency at some point, and prices that in advance.
The probability of this happening rises over time along a saturating curve: it starts
near zero and approaches a ceiling. The daily rate driving that curve was fitted
against historical cases and is 0.021 for Level 4, 0.010 for Level 3, 0.005 for Level
2 and 0.002 for Level 1. The Level 4 figure comes from averaging Mariupol in 2022 and
Aleppo in 2016; the Level 3 figure from Mosul, Goma and the Central African Republic.
The Level 2 and Level 1 figures have no historical anchor at all and are described as
structurally plausible interpolations that require validation. The curve is capped at
95 per cent for Level 4, 80 for Level 3, 60 for Level 2 and 30 for Level 1. Two
modifiers then apply: a blocked corridor, meaning a high D3, raises the probability,
and high urgency imposes a floor, 85 per cent when D6 is 5 and 60 per cent when D6 is
4. The floor exists because of Srebrenica, where the crisis unfolded over three days
and no duration-based curve would have registered it.

The cost of extraction is anchored to the United Nations Humanitarian Air Service,
which is the World Food Programme's air service flying humanitarian staff and light
cargo into places commercial aviation does not serve. Its published operating cost
was 2.08 US dollars per passenger kilometre in 2023. Ground extraction is priced at
30 per cent of that rate, which the code describes as an internal heuristic with no
published source. Air medical evacuation is priced at three times the rate, on the
reasoning that a medical flight carries far fewer passengers. At Level 4 the whole
extraction cost is multiplied by 2.5 for a helicopter premium, which the author
records as unconfirmed: UNHAS does not publish separate helicopter and fixed-wing
rates.

7.4 Field medical treatment. Injuries are estimated from a per-thousand daily rate
that rises with the risk level: zero at Level 0, 0.1 at Level 1, 0.5 at Level 2, 2.0
at Level 3 and 8.0 at Level 4. The code states plainly that no public source reports
in-field civilian injury rates as a daily incidence per thousand, so these are
unvalidated. Each injury is costed at 800 US dollars, modified upward when the
destination has poor medical capacity. The 800 figure sits within a documented
peer-reviewed range: 211 US dollars per surgical case at a conflict-affected mission
hospital in South Sudan in 2022, and roughly 500 to 650 dollars per case at two MSF
surgical trauma centres around 2009, which inflate to roughly 780 and 1,010 dollars
by 2026.

---

## 8. The Break-Even Analysis

8.1 This is the calculation the tool is built around. Two options are compared.
Option A is to evacuate now and then provide assistance to whoever remains behind.
Option B is not to evacuate and to assist the whole population in place. Option A
carries a large one-time cost plus a small daily cost. Option B carries only a daily
cost, but a larger one.

8.2 The break-even day is the one-time evacuation cost divided by the difference
between the two daily costs. If evacuating costs 640,000 US dollars and staying costs
4,000 US dollars a day more than the post-evacuation arrangement, the break-even is
160 days. Before that day, staying is cheaper. After it, evacuation would have been
cheaper.

8.3 What this figure is and is not. It is a resource-planning number. The project's
concept document is emphatic that it is not an answer to whether an evacuation is
worth carrying out. The distinction is that the calculation compares the cost of one
logistics operation against the cost of another logistics operation. It does not
weigh either against lives. The decision to move civilians, the documentation states,
is a matter of legal obligation and humanitarian judgment, not financial
optimisation.

8.4 Transport consistency warnings. The tool also checks the transport mode against
the dimension scores and warns when they are inconsistent. Five patterns trigger a
warning: ground transport with a D4 of 4.0 or above, which indicates logistics
breakdown; ground transport with a D1 of 4.5 or above, which indicates unacceptable
kinetic exposure; walking with a population above 5,000, which is infeasible at
scale; walking with a D2 of 3.5 or above, which means the population cannot walk; and
air transport with a D3 of 4.0 or above, which means airspace authorization is
missing. These are useful precisely because a cost model will happily produce a
plausible-looking figure for an operation that could never be attempted.

---

## 9. Estimating Deaths: The Mortality Model

9.1 What it does. Separately from cost, the tool estimates how many people would die
and be injured if the population stayed. The author's framing is that this provides
scale context for a planning decision, and both the README and the concept document
state that the mortality model is indicative rather than predictive and that the
financial estimates are substantially more reliable.

9.2 The base rate. Each risk level has a baseline death rate expressed per 10,000
people per day. The current values are 0.777 at Level 0, 0.964 at Level 1, 3.625 at
Level 2, 1.805 at Level 3 and 1.000 at Level 4. A reader will immediately notice that
these are not in ascending order, which looks wrong and requires explanation. The
explanation given in the code is that these are not standalone death rates but base
rates that get multiplied by three further factors described below, and that Level 3
in the historical corpus is dominated by urban sieges and city fighting where a high
proportion of the population is directly exposed, while Level 4 is dominated by
large-enclave operations across much bigger populations where per-capita exposure is
lower. The ordering was produced by the fitting procedure rather than assumed, and
the author flags it explicitly as empirically validated but counterintuitive.

9.3 The confinement multiplier. This captures whether people are trapped. It is
calculated as (D3 minus 1) times D4, divided by 5. In plain words: when consent for
movement is absent and logistics have collapsed at the same time, people cannot get
out, and mortality rises sharply. The resulting score is converted into a multiplier
in steps: half at the lowest, then 1, then 2, then 4, then 8 at the highest. An
eightfold difference from a single factor is a very large lever, and its stepwise
rather than smooth form is listed by the author as a known limitation. The anchors
given are Aleppo and Kosovo at a multiplier of 2, Mosul at 1, and the Kherson
evacuation, which had an open corridor, at 0.5.

9.4 The displacement protection factor. If part of the population has already left,
the remaining exposure is lower. The tool reduces the death rate by 60 per cent of the
share that has departed. The 60 per cent coefficient, rather than 100, reflects that
displaced people still face risk on the road, at checkpoints and from exposure. There
is then an important refinement: in a siege, defined as a D3 of 4 or above combined
with a D1 of 4 or above and a population of 500,000 or fewer, the coefficient is
halved to 30 per cent. The reasoning is that in an encircled city, movement itself is
lethal, because civilians pass checkpoints under fire and buses have been attacked.
Displacement is still safer than staying, but only half as much safer as in an open
corridor.

9.5 The geographic exposure factor. Not everyone in a conflict area is under fire at
the same time. Four conflict shapes are recognised, with the fraction of the
population treated as simultaneously exposed given in brackets: urban siege such as
Mariupol or Aleppo (0.85), enclave such as Gaza (0.65), city conflict where a front
line moves through a city, such as Mosul or Kherson (0.40), and regional dispersed
conflict such as Sudan, the Central African Republic or the eastern Democratic
Republic of the Congo (0.12). When the planner has not specified a shape, the tool
infers one from D1 and the population size, on the logic that higher kinetic threat
means more direct fire while a larger population means more dispersion. The
population term uses a logarithm raised to the power 1.4, a refinement introduced
specifically because the earlier formula did not fall away fast enough for
continental-scale conflicts and overestimated Sudan by a wide margin.

9.6 Saturation after 90 days. Cumulative deaths accumulate linearly for the first 90
days and then decelerate along a square-root curve, on the reasoning that populations
adapt and survivors relocate. This also marks the outer edge of the model's intended
planning window.

9.7 Injuries. Injuries are set at four times deaths, following the ICRC planning
ratio. The code notes that a peer-reviewed systematic review implies a ratio closer
to 3.3 to 1, and that frontline-specific figures from Ukraine run far higher, and
retains 4 to 1 as a mid-range planning estimate.

9.8 The infrastructure-denial multiplier. This applies only where there is primary
source documentation that survival infrastructure was deliberately destroyed. It is
calculated as 1 plus 0.4251 times (D1 minus 3) times (D4 minus 3), and only when D1
is at least 4.5 and D4 at least 4.0. It is switched on for four documented cases:
Mariupol, Aleppo, Vukovar and Huambo, giving effective multipliers between roughly
1.6 and 2.3. The supporting documentation cited is a 2024 report on starvation as a
method of warfare in Mariupol, the UN Commission of Inquiry on Syria for hospital
bombing in Aleppo, ICTY proceedings for Vukovar, and Human Rights Watch and Amnesty
reporting on Angola for Huambo. Critically, this multiplier is switched off by default
for live scenarios. The code records why: an earlier version activated it
automatically whenever the dimension thresholds were met, and calibration accuracy
collapsed from 80 per cent to 20 per cent. It is a finding about deliberate atrocity,
not a threshold that can be inferred from slider positions.

---

## 10. How the Model Was Fitted, and Against What

10.1 The historical corpus. The repository contains thirty-one documented conflicts.
Each record holds the population at risk, duration in days, recorded deaths, numbers
displaced and remaining, the estimated vulnerable percentage with its own source and
confidence rating, the distance to safety with its source, all seven dimension scores
assigned retrospectively, corridor status and notes, key lessons, IHL issues, and a
calibration block recording what the model predicted against what was recorded, across
every model version.

10.2 Sixteen cases are used to fit the model: Mariupol 2022, Gaza 2023, Aleppo 2016,
the Kherson evacuation 2022, Mosul 2016, eastern DRC and Goma 2024, the second battle
of Grozny 1999, both battles of Fallujah 2004, the Jenin refugee camp 2002, the siege
of Vukovar 1991, Gaza Cast Lead 2008, Gaza Protective Edge 2014, the siege of West
Beirut 1982, the second Nagorno-Karabakh war 2020, and the siege of Huambo 1993.

10.3 Fifteen are excluded, and the reasons form a clear statement of where the model
does not apply. Duration beyond the 90-day window excludes Sarajevo at 1,425 days,
Kuito in Angola at over 540, Marawi at 154 and the final phase of the Sri Lankan
Vanni offensive at 120. Dispersed regional conflict with no siege perimeter excludes
the Central African Republic in 2014 and Sudan in 2023, the latter also on duration
and on a population of six million. Deliberate massacre as the dominant mechanism of
death, rather than attrition under fire, excludes Srebrenica 1995, Hue 1968, Manila
1945 and Bucha 2022. Open-corridor forced displacement, where civilians were made to
move rather than prevented from moving, excludes Kosovo 1999. Recorded death counts
too uncertain to fit against exclude Misrata 2011, where the contested range runs from
102 to 700.

10.4 Two exclusions are of a different character and the repository says so openly.
Eastern Ghouta 2018 and Gaza Pillar of Defense 2012 are labelled challenge cases and
were excluded, in the words of the data file, to preserve the version 7 metrics. They
document a real structural limit: the Level 4 base rate cannot simultaneously fit a
high-mortality urban siege such as Aleppo, with 31,000 deaths, and a large-enclave
precision operation such as Cast Lead, with 965. The model undercounts one and
overcounts the other by a wide margin. Retaining them in the corpus while removing
them from the fit is a defensible research decision, and the fact that it is
documented rather than concealed is to the project's credit. But a reader should
understand that the headline accuracy figures are calculated on a set from which two
known-difficult cases were removed.

10.5 What was actually fitted. The fitting procedure adjusts six numbers: the five
base death rates and the infrastructure-denial coefficient. It searches for the values
that minimise the mean squared error between the logarithm of predicted deaths and the
logarithm of recorded deaths. Working in logarithms means the procedure fits
proportional rather than absolute error, which is appropriate when the recorded death
counts in the corpus run from 37 to 45,000. The search is constrained so that the
rates for Levels 0, 1 and 2 rise in order; Levels 3 and 4 are deliberately left
unconstrained relative to each other, which is how the counterintuitive ordering
described in Section 9.2 was allowed to emerge.

10.6 The results, and how to read them. On the sixteen fitted cases, the correlation
between predicted and recorded deaths in logarithmic space gives an R-squared of
0.855, meaning the model captures most of the variation in order of magnitude. Seven
of the sixteen cases, or 44 per cent, fall within a factor of two of the recorded
figure. Those two statements sit oddly together and both should be kept in view: the
model is good at ranking conflicts by scale of loss and much less good at predicting
the number for any individual conflict. A battery of statistical checks reported in
the README covers normality of residuals, constant variance, rank correlation and
multicollinearity, and reports Aleppo as the single most influential case.

10.7 One qualification about the cross-validation figure. The reported leave-one-out
R-squared of 0.807 is not produced by refitting the whole model with each case removed
in turn. It fits a straight line through the remaining points in logarithmic space and
predicts the held-out point from that line. It therefore measures how stable the
relationship between predicted and recorded deaths is across the corpus, which is
useful, rather than how well fitted parameters generalise to unseen conflicts, which
is what the term usually implies.

---

## 11. Where the Data Comes From

11.1 UCDP Georeferenced Event Dataset, version 26.1. The Uppsala Conflict Data
Program, based at Uppsala University in Sweden, is the principal academic provider of
data on organised violence worldwide. Its georeferenced dataset records individual
lethal events down to the level of a single village on a single day, with separate
counts for civilian deaths and for each party, and low, best and high estimates
reflecting source uncertainty. ERCF uses it to check its historical cases against an
independent record and to let a planner query recorded violence for a location and
date range. The tool queries the live service where a token is available and falls
back to a locally stored copy of the dataset otherwise.

11.2 ACAPS and the INFORM Severity Index. ACAPS is an independent humanitarian
analysis organisation. Together with the European Commission's Joint Research Centre
it publishes the INFORM Severity Index, a monthly assessment scoring the severity of
humanitarian crises across more than thirty indicators grouped into the impact of the
crisis, the conditions of the people affected, and the complexity of the response.
ERCF uses these scores to colour a world map by country-level severity and to convert
a national severity score onto its own five-level scale. Two things should be noted.
The repository works from a stored table of roughly eighty countries with a live
overlay attempted on top; and the code records that the two relevant ACAPS endpoints
were consistently timing out at the time of writing, which means in practice the
stored table is usually what drives the map. Users should treat the map as an
orientation aid rather than a live feed.

11.3 GeoNames provides city population figures so a planner can start from a real
place rather than a guess. The project's own backlog flags the obvious limitation:
these are pre-conflict populations and do not reflect displacement that has already
occurred, so a user must adjust them manually.

11.4 Open-Meteo provides historical weather from the European reanalysis archive.
ERCF uses fourteen days of temperature, precipitation, snowfall and wind to classify
the operating conditions and to set two multipliers: one on fuel and transport, one on
shelter. Deep winter raises fuel costs by 35 per cent and shelter costs by 120 per
cent, the latter reflecting that cold-climate shelter requires more space per person
and winterised units cost several times a standard tent. A heavy rainy season raises
fuel and transport by 80 per cent, reflecting documented road impassability. If the
planned date is in the future, the tool steps back a year at a time to find comparable
historical conditions and labels the result a planning estimate. The weather data is
tagged as validated; the multipliers derived from it are tagged as estimated.

11.5 A language model is used for one narrow purpose: generating a written country
briefing that summarises the crisis, access conditions, likely exit routes,
neighbouring safe areas, active humanitarian actors and the applicable legal
framework, and proposes starting values for the seven dimensions. If the service is
unavailable the tool falls back to fixed text built from the stored severity table.
This is a convenience feature for a first draft of a scenario. Nothing in the cost or
mortality calculation depends on it.

11.6 Demographic suggestions. For eighteen conflict-affected countries the tool
suggests a vulnerable population percentage. The figure is calculated as the
percentage of children under five, plus the percentage of adults over sixty, plus half
the percentage of people with disabilities. The halving is to avoid double-counting
people who are both elderly and disabled, and to reflect that only some disabilities
create evacuation-relevant constraints. The underlying figures come from UNICEF's
State of the World's Children 2023 and the UN World Population Prospects 2022, with a
uniform 15 per cent disability figure drawn from the WHO World Report on Disability.
The results range from 21.5 per cent for Syria, Iraq and Libya to 36.5 per cent for
Ukraine, where the driver is an unusually large elderly population. Two caveats
matter: the child component counts only children under five rather than all minors,
and the disability figure is a global average applied uniformly, whereas conflict-
affected populations are known to have higher rates. The suggestion is advisory and
the planner confirms or dismisses it.

11.7 Other transport modes. Two supplementary models exist. Air evacuation prices
fixed-wing movement at the same UNHAS rate of 2.08 US dollars per passenger kilometre
and helicopter movement from a United Nations procurement contract for a Mi-8
airframe divided by an assumed number of guaranteed flight hours, returning a low,
mid and high band rather than a single figure, with a deliberately conservative 50 per
cent load factor. It plans fleet size across one, three, seven, fourteen and thirty
day windows. Walking evacuation interpolates group speed between 8 kilometres per hour
for healthy adults and 3 kilometres per hour for a fully vulnerable group, the latter
taken from published gait-speed data for adults over 65, and assumes 8 walking hours a
day rather than the 15 used in the academic migration model it draws on. It contains
no attrition or mortality term at all, reports only the number of days of exposure,
and states explicitly that the exposure does not feed back into the danger or urgency
dimensions: that remains the analyst's judgment. Both models are marked as less
validated than the ground transport model, and the backlog records that walking is not
yet wired into the break-even calculation.

---

## 12. Reading the Results

12.1 The interface is a single web page with several sections. The Scenario Builder
holds the seven sliders and the population, vulnerability, distance and terrain
inputs, and updates every figure as the sliders move. A cost breakdown itemises the
evacuation estimate line by line. A decision analysis panel shows the break-even chart
with the two cost lines crossing. Historical Cases lists all thirty-one conflicts with
badges marking which are out of scope and which are challenge cases. Compare on Radar
overlays the current scenario's seven scores against any historical case as a
seven-pointed shape, alongside a table comparing population, cost, cost per evacuee,
duration and deaths. Map View colours the world by severity. A references section
lists the data sources, and a methodology panel documents the statistical validation.

12.2 What the radar comparison is for. Experienced coordinators reason by analogy,
saying that a situation resembles Mosul or resembles Mariupol. The radar overlay makes
that comparison explicit and checkable, by showing exactly which of the seven
dimensions match and which do not. That is a modest but genuine contribution: it turns
an intuition into something a colleague can disagree with.

12.3 Cost benchmarking. Three real operations are provided for context: the Kosovo
Humanitarian Evacuation Programme in 1999, which moved 60,549 people at roughly 562 US
dollars each; Libya in 2011 at roughly 984 dollars; and the evacuation of about 15,000
people from Lebanon to Canada in 2006 at several thousand dollars each. The README is
careful to explain why these exceed the model's own figures by a wide margin: ERCF
prices the immediate field operation only, at roughly 134 US dollars per person for a
Level 2 ground movement over 50 kilometres, while real operations include
international transport, reception facilities and weeks of hosting. A user comparing
the tool's output to a real operation without reading that note would draw the wrong
conclusion.

---

## 13. Grounding in International Humanitarian Law

13.1 Each risk level is tied to a stated legal reference. At Level 1 the tool cites
the right of voluntary departure under Article 35 of the Fourth Geneva Convention. At
Level 2 it cites the precautionary obligations in Articles 57 and 58 of Additional
Protocol I, which require parties to take feasible precautions to spare civilians,
including effective advance warning, and to keep civilians away from military
objectives. At Level 3 it cites Article 49 of the Fourth Geneva Convention. At Level 4
it cites the same article's prohibition on forcible transfer and the corresponding
provision of the Rome Statute of the International Criminal Court.

13.2 Article 49 is the central provision and deserves setting out. It prohibits
individual or mass forcible transfers and deportations of protected persons from
occupied territory, regardless of motive. It then creates a narrow exception: an
Occupying Power may undertake total or partial evacuation of a given area if the
security of the population or imperative military reasons so demand. Such evacuations
must not move people outside the occupied territory unless it is materially impossible
to avoid, and those evacuated must be returned home as soon as hostilities in the area
have ceased. The ICRC commentary is emphatic that "imperative" means an absolute
constraint leaving no other choice, not military convenience or advantage.

13.3 Why this matters for a cost tool. The exception in Article 49 turns on necessity,
not on cost or convenience. A tool that produced a number and called it a
recommendation would risk implying that an evacuation which is expensive is therefore
not demanded, which inverts the legal test. ERCF's stated philosophy addresses this
directly: labels are descriptive, not imperative; a Level 4 classification describes a
risk profile and does not order an action. The break-even day is presented as a
resource-planning figure, not as a decision rule.

13.4 The framework also draws on Sphere standards throughout for its quantities. The
Sphere Handbook is the humanitarian sector's most widely used set of minimum standards
for response, developed collectively by humanitarian organisations, covering water and
sanitation, food security, shelter and health. It is a standards document rather than a
costing document, which is precisely the boundary ERCF has to cross: Sphere tells the
model how many litres and how many square metres, but not what they cost.

---

## 14. The Ethical Position

14.1 A tool that computes the cost of evacuating people and the cost of not
evacuating them invites an obvious objection. The repository addresses it in a notice
displayed in the interface itself and repeated in the concept document: the tool
estimates the operational cost of humanitarian evacuation logistics, in order to
support planning and resource mobilisation, and does not place a monetary value on
human life.

14.2 The structural safeguards behind that claim are worth naming, because they are
design decisions rather than assertions. Cost and mortality are computed by separate
functions and never combined into a single index; there is no cost-per-life-saved
figure anywhere in the codebase. The mortality output is described in the
documentation as contextual support only, not a target, threshold or measure of
acceptable loss. The break-even calculation compares one logistics operation against
another logistics operation, never against a count of deaths. And the concept document
states explicitly that the tool is not intended to determine whether an evacuation is
worth it or to rank the value of civilian lives.

14.3 The residual risk remains, and it is the risk that attaches to any costing tool
in this domain: a figure produced for a funding appeal can be repurposed in an argument
about whether to act. The separation in the software is real, but it depends on the
people using the output to maintain the same separation.

---

## 15. Notable Inconsistencies Found in Review

A plain-language review is of limited value if it only reports what the documentation
claims. The following discrepancies were found by reading the code against the
documentation. None is fatal, and several are the ordinary residue of a fast-moving
research project, but a reader relying on the repository should know about them.

15.1 The acronym itself is used inconsistently. The README and both design documents
give ERCF as the Evacuation Risk and Cost Framework. The prompt used for generating
country briefings expands it as the Evacuation Risk Classification Framework. This
report follows the README.

15.2 Several explanatory comments have fallen out of step with the code they describe.
The explanation attached to the in-zone assistance calculation still lists access
multipliers of 1.0, 1.5, 3.0, 5.0 and 8.0, while the values actually used are 1.0,
1.5, 2.0, 3.6 and 4.0. The same explanation gives a treatment cost of 1,200 US dollars
per injury, while the code applies 800. In both cases the values in force are the more
conservative and better-evidenced ones, so the effect is that the documentation
overstates the model's outputs rather than understating them. A summary string
displayed with the evacuation results still reports the Sphere emergency minimum of 15
litres of water per person per day although the calculation uses 20.

15.3 The README describes the historical corpus as covering 1991 to 2024. The earliest
case in the data file is the battle of Manila in 1945, and the corpus also includes Hue
in 1968 and West Beirut in 1982. The correct range is 1945 to 2024.

15.4 One of the calibration scripts contains a file path pointing at a directory on the
original author's own computer, which means it will not run on a fresh copy of the
repository without editing that line. The main calibration script runs correctly. A
comment in that script still refers to twenty in-scope cases, although it counts them
dynamically and in practice uses sixteen.

15.5 The demographic dataset contains a country code entry for Mali that does not match
that country's actual three-letter code, so a lookup by code would fail for Mali while
a lookup by name succeeds.

---

## 16. Maturity, and What Remains Unbuilt

16.1 The core of ERCF is genuinely built. The seven-dimension scoring, the evacuation
cost model, the in-zone assistance model, the break-even analysis, the mortality model,
the historical corpus, the calibration pipeline, the statistical validation, the
transport warnings, the radar comparison and the map are all implemented and running.
The calibration can be reproduced by anyone who clones the repository and runs a single
command. This is not a mock-up.

16.2 What the project's own backlog lists as outstanding is instructive, and it divides
into three groups. In the first are features that would improve the tool as it stands:
making fuel, food and medical supply prices adjustable per country, showing the user
when the external data was last updated, adding a structured flag for cases involving
mass atrocity rather than leaving it in free text, and building a pipeline for adding
new historical cases and re-running the fit. In the second are capabilities the tool
does not currently have: the dimension scores are a static snapshot with no modelling
of how a conflict escalates over time, only one evacuation route can be assessed at a
time, walking evacuation is not integrated into the break-even calculation, and there
is no export to a document format that a funding appeal could use directly. In the
third are research questions: expert-panel validation of the seven weights, resolving
the Level 4 structural limitation that the two challenge cases document, and putting
confidence intervals around the cost estimates, which are currently single point
figures.

16.3 That last item deserves emphasis. Every cost figure the tool produces is a single
number built from parameters that the project itself classifies as validated, estimated
or unvalidated. A total assembled from a validated water quantity, an uncited food
price, an estimated tent price and an unvalidated access multiplier is not a number
with uniform reliability, and at present the interface does not show a range around it.

16.4 A companion module, RICS, the Resettlement and Inclusion Capacity Simulator, sits
in a subdirectory of the same repository. It applies the same cost and break-even
machinery to a different question: the long-term cost of a protracted refugee camp
against the upfront cost of local integration, with Dzaleka camp in Malawi as its
worked case. Its architecture is built out, with roughly two thousand lines of Python
and a working interface, and it introduces two design ideas worth noting: a
requirement, enforced by the database itself rather than by policy, that no group
smaller than twenty people can be recorded, so that no individual can be identified;
and a decision to propagate uncertainty into the cost estimate by widening each
parameter into a band according to how well evidenced it is, rather than by simulation.
But RICS is scaffolding at present. Several of its key parameters are unset
placeholders, its readiness parameters are inherited wholesale from another tool and
tagged unvalidated, and its own design document says that its central coefficient
awaits calibration against real camp data. It should be read as a design proposal with
working plumbing, not as a second finished tool.

16.5 Relationship to the India evacuation simulator. A copy of a second Ethical Tech
CoLab project sits in the repository as a reference. That tool, the Evacuation
Readiness and Uncertainty Simulator, asks a different question: not what an evacuation
costs, but how confident an assessment of readiness can be. It scores candidate
destinations across seven factors, three of which are treated as gatekeepers, meaning
that security, authority consent and host willingness each individually cap readiness
at twenty per cent if blocked, no matter how good everything else looks. It runs five
hundred simulations per pairing under a global uncertainty setting, in order to show
that identical assessed readiness produces materially different predicted outcomes as
confidence degrades. Its two epistemic distinctions are worth carrying into any reading
of ERCF: that a confidently identified gap is better than an unreliably assessed one,
and that Unknown and Unwilling must never be conflated, because an intelligence gap can
be closed while a confirmed refusal cannot. The two projects share a documentation
structure and an author, and they are the two parents of RICS, which ports the cost
engine from ERCF and the readiness engine from the simulator. This report treats ERCF
on its own terms; the simulator is not required to understand it.

---

## 17. Limitations and Caveats

Beyond the specific issues in Sections 15 and 16, the following limitations apply to
the framework as a whole.

17.1 The weights are unvalidated. All seven are the author's modelled estimates. No
expert panel has reviewed them.

17.2 The dimension scores are a snapshot. There is no modelling of escalation. A
conflict that will look completely different in three weeks is scored as it looks
today.

17.3 The planning window is 90 days. Beyond that, mortality accumulation is subject to
a saturation adjustment and the model is outside the range of its own calibration data.

17.4 The mortality model fits scale, not individual cases. Fewer than half the fitted
cases fall within a factor of two of their recorded death tolls. The model is useful
for indicating whether a situation is in the hundreds, the thousands or the tens of
thousands, and should not be used for anything finer.

17.5 The model has documented blind spots. It does not capture deliberate massacre or
genocide, where death occurs in days rather than accumulating through attrition. It
does not capture famine or the collapse of healthcare under blockade, which the code
identifies as a major driver of mortality in Gaza that the seven dimensions do not
represent. It underestimates open-corridor forced displacement, because it assumes a
population trapped under fire rather than one compelled to move.

17.6 The most consequential cost multipliers are the least evidenced. The access
multiplier that governs the entire in-zone assistance calculation is unconfirmed at its
highest level, and the loss rates at Levels 2, 3 and 4, which reach fifty per cent, have
no published equivalent that the author could locate.

17.7 Population figures are pre-conflict. City populations retrieved automatically do
not account for displacement that has already taken place, and must be adjusted by hand.

17.8 The tool models one corridor. Real evacuation planning compares routes.

17.9 The historical corpus is small. Sixteen fitted cases is enough to sanity-check a
framework, not enough to support statistical generalisation, and two known-difficult
cases were held out of the fit.

17.10 Above all, this is a research prototype produced by one researcher with academic
supervision. Its own README states that it does not constitute operational advice and
that all estimates require validation against country-specific intelligence and field
assessment before any operational application.

---

## 18. Intended Audience and Use

18.1 The concept document identifies five groups: humanitarian programme officers
producing rapid cost estimates for funding proposals, emergency coordinators comparing
scenarios before a crisis escalates, donors and fund managers benchmarking against
documented operations, researchers studying civilian protection frameworks, and
government civil protection agencies doing preparedness planning.

18.2 The most defensible use of the tool today is the one furthest from an active
crisis: preparedness planning, funding appeal preparation, and teaching. Its value in
those settings does not depend on the precision of any individual figure. It depends on
forcing a planner to state, in numbers, what they are assuming about vehicle capacity,
staff ratios, supply losses and access costs, and on making those assumptions available
for a colleague to contest.

18.3 The tool is explicitly not a real-time conflict monitoring system, not a
forecasting model, not a mass casualty prediction tool, and not a substitute for field
assessment or expert judgment. The repository states each of these explicitly.

---

## 19. Conclusion

19.1 ERCF's contribution is not a set of accurate numbers. It is the assembly of
scattered, separately published operational standards into one calculation that can be
run, inspected and argued with, together with an unusually disciplined habit of
recording where each number came from and how far it can be trusted. The source code
reads in places less like software than like a research notebook, documenting failed
searches, revised assumptions, and figures that were lowered when the evidence would not
support them. A model that reduced its own access multipliers from eight to four because
no published source went above four is behaving the way a research instrument should.

19.2 The framework's structural insight is the separation it maintains between the
danger a population faces and the practicality of moving it, carried through into the
separation of cost from mortality and of description from recommendation. This keeps the
legal question, which turns on necessity, from being quietly answered by an operational
one, which turns on difficulty.

19.3 The prototype's weakest point is also clearly visible: the parameters carrying the
most weight in the in-zone assistance calculation are the ones with the least published
support behind them, and the mortality model resolves scale rather than magnitude. The
author says so in the code, in the README and in the concept document. A reader should
take the transparency as an invitation to check the work rather than as a reason to skip
checking it.

19.4 What a tool of this kind can reasonably offer today is a structured first estimate,
produced in an hour rather than a week, with every assumption on the surface where a
humanitarian planner, a donor or a lawyer can see it and challenge it. That is a real
contribution to a decision that is currently made largely from memory, and it is offered
here without the claim that the numbers themselves are yet good enough to act on.

---

## Attribution

Developed by Yago Rocha as part of research on International Humanitarian Law and
civilian protection at the NYU Center for Global Affairs (2026), under the Ethical Tech
CoLab. The repository records the work as presented to Teresa Cantero, PhD Researcher,
whose suggestions are cited in the project backlog.

> Note: This report is a plain-language summary of a research prototype. The prototype
> is for academic demonstration only. Its outputs are indicative and are not a
> substitute for operational decision-making, legal advice, or assessment by qualified
> humanitarian and IHL professionals. All cost figures represent logistics estimates.
> The tool does not place a monetary value on human life.
