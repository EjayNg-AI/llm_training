# Final OWT Tokenizer Report: 1GB Probe vs Full (2.5M Caps)

- Generated (UTC): `2026-03-01T07:04:09Z`
- Probe run: `owt32k_probe_1gb_25m_20260301_060954` / `tokenizer_owt32k_probe_1gb_25m_20260301_060954`
- Full run: `owt32k_full_25m_20260301_061344` / `tokenizer_owt32k_full_25m_20260301_061344`

## Source Files
- Probe run statistics: `artifacts/tokenizer/runs/owt32k_probe_1gb_25m_20260301_060954/run_statistics.json`
- Full run statistics: `artifacts/tokenizer/runs/owt32k_full_25m_20260301_061344/run_statistics.json`
- Full export directory: `artifacts/tokenizer/exports/tokenizer_owt32k_full_25m_20260301_061344`
- A/B report: `artifacts/tokenizer/reports/ab_compare_probe_vs_full_25m.md`

## Environment + Config Snapshot
| Field | Probe | Full |
|---|---:|---:|
| OS | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` |
| Platform Mode | `WSL` | `WSL` |
| CPU | `Intel(R) Core(TM) Ultra 7 155U` | `Intel(R) Core(TM) Ultra 7 155U` |
| RAM (GB) | `15.354` | `15.354` |
| Python | `3.12.3` | `3.12.3` |
| regex | `2026.2.19` | `2026.2.19` |
| min_piece_freq | `2` | `2` |
| max_unique_pieces | `2500000` | `2500000` |
| max_word_types | `2500000` | `2500000` |
| max_piece_bytes | `200` | `200` |
| vocab_size | `32000` | `32000` |
| min_merge_freq | `2` | `2` |
| max_merges | `None` | `None` |
| num_workers | `4` | `4` |
| batch_lines | `2000` | `2000` |

## Stage 1 Comparison
| Run | total_bytes | total_lines | total_pieces_seen | unique_before_cap_window | unique_after_min_freq | unique_kept | hit_cap | cap_events | cutoff_freq | coverage | RSS_peak_mb | RSS_end_mb | t_stage1_s |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| Probe 1GB (2.5M) | 1073741856 | 8527049 | 223176190 | 1419176 | 706249 | 706249 | no | 0 | 2 | 0.996806 | 269.723 | 183.324 | 64.917 |
| Full (2.5M) | 11920511059 | 94568885 | 2476979902 | 2524976 | 2500000 | 2500000 | yes | 368 | 2 | 0.997890 | 518.000 | 427.469 | 1766.177 |

## Stage 2 Comparison
| Run | word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb | t_stage2_s |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| Probe 1GB (2.5M) | 706249 | 706249 | no | 2 | 8.254 | 14 | 198 | 324.422 | 2.352 |
| Full (2.5M) | 2500000 | 2500000 | no | 2 | 8.791 | 15 | 200 | 744.746 | 5.424 |

## Stage 3 Comparison
| Run | merges_done | t_stage3_s | median_ms/merge | p95_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | candidates_post_median | candidates_pre_p95 | candidates_post_p95 | snapshots | snapshot_total_s | wal_sync_count | wal_sync_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Probe 1GB (2.5M) | 31742 | 56.212 | 0.234 | 3.129 | 926.445 | 11069 | 580092 | 9.000 | 1519.000 | 649.000 | 31 | 0.073 | 159 | 0.451 |
| Full (2.5M) | 31742 | 205.108 | 0.676 | 11.897 | 2623.695 | 15789 | 1574627 | 25.000 | 6099.000 | 2427.000 | 31 | 0.067 | 159 | 0.462 |

## A/B Stability (Probe=A vs Full=B)
- Run A: `owt32k_probe_1gb_25m_20260301_060954`
- Run B: `owt32k_full_25m_20260301_061344`
- Held-out path: `openwebtext_sample_3k_4k_tokens.txt`
- Merge overlap@1k: `0.998000`
- Merge overlap@5k: `0.986400`
- Merge overlap@10k: `0.977300`
- tokens/char delta (B-A): `-0.000402484`
- tokens/word delta (B-A): `-0.002439875`

## Key Deltas (Full - Probe)
- Stage 1 bytes: `11920511059 - 1073741856 = 10846769203`
- Stage 1 lines: `94568885 - 8527049 = 86041836`
- Stage 1 coverage delta: `0.001085`
- Stage 3 median ms/merge delta: `0.442331`

## Full Run Appendix: Last 1000 Vocab Entries (by token ID)
- Source: `artifacts/tokenizer/exports/tokenizer_owt32k_full_25m_20260301_061344/vocab.json`
- Token IDs included: `31000` through `31999`

```text
id	token_unicode_escape
31000	\u0120multiply
31001	\u0120shrine
31002	\u0120Tet
31003	\u0120articulated
31004	\u0120Nordic
31005	\u0120infinitely
31006	138
31007	\u0120cakes
31008	lections
31009	\u0120democracies
31010	\u0120unheard
31011	charging
31012	wives
31013	\u0120Parent
31014	\u0120exited
31015	\u0120defy
31016	\u0120degener
31017	\u0120Sabha
31018	\u0120java
31019	ursed
31020	piring
31021	\u0120REST
31022	\u0120Tray
31023	\u0120ONLY
31024	\u0120Kingston
31025	\u0120infield
31026	affle
31027	................................
31028	\u0120privatization
31029	\u0120lia
31030	\u0120recharge
31031	\u0120gust
31032	\u0120Bowman
31033	IFF
31034	\u0120dividend
31035	\u0120stumble
31036	\u0120Spons
31037	\u0120hunted
31038	\u0120ga
31039	plot
31040	\u0120supervisors
31041	\u0120Irvine
31042	frey
31043	onding
31044	\u0120\xc3\xa4
31045	\u0120succeeding
31046	\u0120intoxicated
31047	\u0120dispersed
31048	\u0120MySQL
31049	hate
31050	\u0120ensh
31051	\u0120Allies
31052	\u0120legalizing
31053	\u0120fulfillment
31054	\u0120Natalie
31055	\u0120Monsters
31056	anie
31057	omsky
31058	\u0120Supply
31059	Install
31060	\u0120hassle
31061	\u0120profitability
31062	){
31063	Reb
31064	\u0120JD
31065	\u0120smashing
31066	\u0120horribly
31067	\u0120``
31068	members
31069	\u0120menace
31070	sin
31071	\u0120TED
31072	estation
31073	Initially
31074	\u0120chimpanz
31075	\u0120apocalypse
31076	Official
31077	\u0120Nicholson
31078	\u0120handcuffed
31079	\u0120timetable
31080	\u0120Higgins
31081	\u0120backlog
31082	\u0120Plains
31083	\u0120concerted
31084	\u0120Zombie
31085	\u0120Makes
31086	\u0120spheres
31087	\u0120solicit
31088	\u0120Daesh
31089	\u0120councillors
31090	\u0120scenery
31091	\u0120morp
31092	\u0120Chronicles
31093	\u0120stainless
31094	201
31095	+.
31096	\u0120brilliantly
31097	anza
31098	\u0120dominates
31099	\u0120fortress
31100	\u0120terminals
31101	pick
31102	\u0120Pump
31103	\u0120humorous
31104	\u0120Mayweather
31105	\u0120Burr
31106	\u0120inflict
31107	\u0120technicians
31108	\u0120Graphics
31109	osate
31110	\u0120comforting
31111	\u0120..........
31112	\u0120Mafia
31113	\u0120stewards
31114	\u0120Maharashtra
31115	USD
31116	\u0120knot
31117	\u0120seismic
31118	sound
31119	\u0120CFL
31120	\u0120bulbs
31121	\u0120depl
31122	\u0120chast
31123	aptic
31124	env
31125	\u0120disillusion
31126	amphetamine
31127	cars
31128	\u0120avenue
31129	\u0120Sle
31130	\u0120Pau
31131	\u0120Millennium
31132	\u0120enzymes
31133	\u0120Arbor
31134	\u0120Portal
31135	Config
31136	earance
31137	\u0120Zerg
31138	whelming
31139	Brazil
31140	\u0120137
31141	\u0120Parliamentary
31142	terrorist
31143	nov
31144	141
31145	\u0120Enough
31146	\u0120culinary
31147	\xc4\u0141an
31148	\u0120redevelopment
31149	\u0120poisonous
31150	Secretary
31151	loid
31152	\u0120Recession
31153	\u0120SHARES
31154	vm
31155	opsis
31156	\u0120bum
31157	astical
31158	###
31159	\u0120recounts
31160	\u0120miner
31161	\u0120Capitals
31162	\u0120Regular
31163	\u0120Sounders
31164	\u0120undefeated
31165	\u0120Kaplan
31166	\u0120clamp
31167	\u0120issu
31168	\u0120ballpark
31169	\u0120altru
31170	\u0120Sharif
31171	\u0120Ventures
31172	\u0120Rousse
31173	PRO
31174	Swed
31175	istas
31176	\u0120gram
31177	enburg
31178	\u0120Fashion
31179	\u0120Pett
31180	\u0120480
31181	\u0120encro
31182	\u0120Byz
31183	\u0120Bernanke
31184	rupal
31185	\u0120Lotus
31186	forestation
31187	obar
31188	\u0120creamy
31189	\u0120mating
31190	\u0120enumer
31191	\u0120affirmed
31192	\u0120Pipeline
31193	brow
31194	\u0120Nichols
31195	\u0120Sharma
31196	\u0120benefiting
31197	\u0120Boise
31198	\u0120Wen
31199	\u0120elevate
31200	\u0120overcrowd
31201	\u0120Hastings
31202	\u0120unthinkable
31203	\u0120uneasy
31204	\u0120southeastern
31205	\u0120Nept
31206	\u0120Essex
31207	update
31208	ARR
31209	\u0120coolest
31210	\u0120outper
31211	\u0120convened
31212	\u0120Borg
31213	\u0120funn
31214	atcher
31215	\u0120intrusion
31216	orrh
31217	\u0120skipping
31218	\u0120138
31219	\u0120deadliest
31220	\u0120stirred
31221	\u0120Bentley
31222	\u0120Wah
31223	\u0120downhill
31224	clipse
31225	\u0120civilizations
31226	\u0120groundwork
31227	\u0120upsetting
31228	\u0120deficiencies
31229	\u0120cd
31230	\u0120citations
31231	plays
31232	\u0120dismissing
31233	\u0120cleric
31234	\u0120constraint
31235	\u0120Contribut
31236	immers
31237	\u0120consolidated
31238	\u0120lavish
31239	ruly
31240	\u0120Pistons
31241	\u0120Vanderbilt
31242	rapping
31243	\u0120battalion
31244	\u0120Dexter
31245	Target
31246	\u0120sap
31247	\u0120Clo
31248	\u0120welcomes
31249	\u0120increment
31250	\u0120vectors
31251	\u0120youthful
31252	Die
31253	\u0120dams
31254	idental
31255	\u0120cornerstone
31256	violence
31257	\u0120inconvenience
31258	\u0120quantify
31259	\u0120narrowed
31260	Charlie
31261	vig
31262	result
31263	\u0120slows
31264	\u0120discrepancy
31265	\u0120Sutton
31266	\u0120saint
31267	\u0120shines
31268	\u0120transitional
31269	\u0120Clause
31270	???
31271	\u0120refurb
31272	Series
31273	\u0120ozone
31274	\u0120lymph
31275	\u0120repr
31276	|>[
31277	MG
31278	\u0120DSL
31279	\u0120menstru
31280	\u0120Residents
31281	\u0120adept
31282	\u0120Francois
31283	\u0120offend
31284	\u0120avatar
31285	\u0120freeing
31286	proclaimed
31287	\u0120Burlington
31288	adena
31289	numbered
31290	avour
31291	\u0120indifferent
31292	\u0120Mostly
31293	testing
31294	guyen
31295	AU
31296	agrams
31297	\u0120spar
31298	zsche
31299	indal
31300	\u0120phon
31301	\u0120Glory
31302	Jeremy
31303	iples
31304	atlantic
31305	\u0120Pf
31306	\u0120precautions
31307	\u0120swelling
31308	\u0120hypotheses
31309	Ford
31310	\u0120Elf
31311	geons
31312	\u0120regeneration
31313	\u0120Fang
31314	\u0120warp
31315	\u0120technician
31316	ichick
31317	begin
31318	\u0120brilliance
31319	\u0120scrambled
31320	oppable
31321	\u0120indefinite
31322	\u0120noodles
31323	ttle
31324	hello
31325	\u0120sewer
31326	147
31327	\u0120vertically
31328	\u0120Ubisoft
31329	\u0120sprayed
31330	Jess
31331	xi
31332	\u0120aloud
31333	\u0120OEM
31334	urers
31335	\u0120Plans
31336	igans
31337	\u0120reconnaissance
31338	\u0120Albuquerque
31339	\u0120fraught
31340	erno
31341	\u0120cooled
31342	\u0120\xcd
31343	Hom
31344	\u0120131
31345	Dom
31346	\u0120Theft
31347	steen
31348	\u0120Collective
31349	Half
31350	azard
31351	\u0120./
31352	\u0120Designer
31353	\u0120134
31354	\u0120Grill
31355	\u0120hurricanes
31356	)}
31357	\u0120Pratt
31358	\u0120RED
31359	\u0120Thames
31360	\u0120tariff
31361	\u0120Hak
31362	\u0120vodka
31363	\u0120declarations
31364	\u0120sparking
31365	\u0120MON
31366	\u0120como
31367	opian
31368	\u0120VW
31369	\u0120lecturer
31370	\u0120cavalry
31371	\u0120stif
31372	\u0120Biblical
31373	\u0120runaway
31374	pron
31375	\u0120cameo
31376	\u0120trustworthy
31377	\u0120compromises
31378	\u0120Plat
31379	\u0120Enemy
31380	\u0120fooled
31381	\u0120tumult
31382	\u0120salvage
31383	\u0120Perman
31384	\u0120defaults
31385	\u0120Photography
31386	\u0120Songs
31387	\u0120nonpartisan
31388	\u0120Lovecraft
31389	Apart
31390	\u0120Chick
31391	\u0120positives
31392	hydro
31393	umpy
31394	\u0120Compar
31395	\u0120listens
31396	\u0120favoured
31397	ouf
31398	\u0120Alto
31399	\u0120torso
31400	\u0120calmly
31401	\u0120Fior
31402	Fit
31403	\u0120hygiene
31404	Energy
31405	\u0120Ci
31406	\u0120deposition
31407	\u0120occult
31408	olin
31409	\u01201925
31410	\u0120ensued
31411	addock
31412	\u0120outfielder
31413	stasy
31414	\u0120Legendary
31415	itud
31416	\u0120establishes
31417	\u0120disqual
31418	*.
31419	Word
31420	\u0120vested
31421	\u0120slips
31422	\u0120Semin
31423	\u0120DAY
31424	\u0120bland
31425	\u0120finalists
31426	\u0120Boat
31427	\u0120graveyard
31428	\u0120qualifier
31429	\xd1\u0122\xd0\xb5
31430	Simon
31431	\u0120Borders
31432	OTUS
31433	\u0120Minds
31434	\u0120Turbo
31435	Brexit
31436	\u0120OPS
31437	\u0120nominate
31438	tesque
31439	\u0120Theodore
31440	cery
31441	\u0120amenities
31442	jiang
31443	slist
31444	\u0120Aby
31445	\u0120Pike
31446	\u0120Marvin
31447	\u0120Woody
31448	\u0120Olive
31449	Initial
31450	\u0120Euros
31451	\u0120Evening
31452	\u0120Merrill
31453	Residents
31454	hetti
31455	\u0120goats
31456	apego
31457	\u0120Opinion
31458	\u0120ancestral
31459	oirs
31460	uo
31461	\u0120enriched
31462	\u0120Slav
31463	\u0120Isaiah
31464	\u0120Fran\xc3\xa7
31465	\u0120euth
31466	aura
31467	\u0120fracture
31468	\u0120Gins
31469	comments
31470	\u0120reversing
31471	\u0120midway
31472	\u0120Variety
31473	poor
31474	random
31475	\u0120fres
31476	\u0120ascent
31477	phot
31478	\xe2\u0122\xa6<|
31479	\u0120presses
31480	ERC
31481	croft
31482	cert
31483	\u0120shortfall
31484	perture
31485	ICT
31486	\u0120Leonardo
31487	ispensable
31488	\u0120tainted
31489	independent
31490	iddy
31491	\u0120complicit
31492	authored
31493	\u0120segregated
31494	\u0120conditioned
31495	\u0120distressed
31496	\u0120unsigned
31497	\u0120deductions
31498	\u0120Programming
31499	\u0120SEAL
31500	\u0120redesigned
31501	\u0120glitch
31502	scars
31503	\u0120persecuted
31504	abytes
31505	\u0120remedies
31506	\u0120nm
31507	\u0120aval
31508	EAR
31509	\u0120playful
31510	shop
31511	*,
31512	\u0120harming
31513	\u0120Sunshine
31514	\u0120Gibbs
31515	\u0120unres
31516	ahi
31517	\u0120Cyn
31518	endon
31519	\u0120Terran
31520	\u0120compositions
31521	\u0120humiliating
31522	\u0120Chess
31523	gre
31524	\u0120singers
31525	ilingual
31526	\u0120reproduced
31527	\u0120Bolivia
31528	Permalink
31529	\u0120archaeologists
31530	\u0120eclips
31531	...)
31532	\u0120freaking
31533	\u0120hubs
31534	\u0120empowerment
31535	\u0120Suzuki
31536	none
31537	\u0120Anfield
31538	AX
31539	\u0120Platinum
31540	\u0120selfie
31541	\u0120endorsements
31542	Manchester
31543	rm
31544	\u0120delightful
31545	communication
31546	CI
31547	\u0120vitamins
31548	\u0120PLAY
31549	\u0120exhaustion
31550	acha
31551	\u0120eternity
31552	xc
31553	\u0120translating
31554	\u0120confidentiality
31555	Obs
31556	cards
31557	\u0120preach
31558	\u0120Coke
31559	\u0120travers
31560	Probably
31561	\u0120inactive
31562	\u0120Sew
31563	\u0120peasant
31564	css
31565	\u0120durability
31566	\u0120regained
31567	Travel
31568	assadors
31569	\u0120Ud
31570	\u0120discard
31571	eson
31572	\u0120Hale
31573	\u0120mayors
31574	\u0120misled
31575	\u0120offensively
31576	ODE
31577	galitarian
31578	\u0120Cedar
31579	Disney
31580	\u0120mural
31581	\u0120Intercept
31582	\u0120Kling
31583	\u0120Marian
31584	\u0120revolutions
31585	\u0120calorie
31586	opening
31587	\u0120gubernatorial
31588	Pros
31589	\u0120Slack
31590	\u0120GNOME
31591	\u0120Comet
31592	\u0120();
31593	\u0120modifying
31594	\u0120dehyd
31595	aldi
31596	\u0120Railroad
31597	\xc3\xa6
31598	ographs
31599	\u0120Vega
31600	148
31601	\u0120coma
31602	\u0120steadfast
31603	\u0120subscriptions
31604	\u0120forcefully
31605	\u0120harbour
31606	\u0120Fantastic
31607	\u0120Methods
31608	alan
31609	\u0120Billion
31610	\u0120salute
31611	\u0120guarding
31612	\u0120unveil
31613	Average
31614	\u0120greeting
31615	Fall
31616	\u0120Unt
31617	bley
31618	\u0120compiling
31619	ractions
31620	\u0120coping
31621	\u0120Islamabad
31622	ridges
31623	Cook
31624	\u0120bewild
31625	\u0120OB
31626	conference
31627	\u0120prosecuting
31628	\u0120annexation
31629	\u0120restraining
31630	\u0120cloak
31631	wolves
31632	\u0120repealing
31633	hetto
31634	\u0120Paula
31635	']
31636	\u0120pointers
31637	\u0120Blvd
31638	\u0120paramount
31639	\u0120consolidate
31640	Across
31641	\u0120fuzzy
31642	\u0120Tayyip
31643	Hack
31644	oki
31645	\u0120Shoot
31646	\u0120manageable
31647	\u0120solemn
31648	\u0120groceries
31649	\u0120conveyed
31650	\u0120epilepsy
31651	\u0120unatt
31652	\u0120widget
31653	\u0120Kauf
31654	iliary
31655	Len
31656	\u0120Known
31657	\u0120Babylon
31658	\u0120Supporters
31659	\u0120scratching
31660	\u0120Ashton
31661	Sov
31662	hemy
31663	\u0120Kry
31664	\u0120Prosecutor
31665	\u0120behaving
31666	\u0120squash
31667	\u0120Witt
31668	nails
31669	\u0120promo
31670	inflamm
31671	\u0120enclosed
31672	\u0120Shooting
31673	\u0120billboard
31674	REAK
31675	utan
31676	\u0120Daddy
31677	\u0120unwit
31678	ielding
31679	\u0120sandbox
31680	ousand
31681	fing
31682	\u0120Certain
31683	cipled
31684	ggles
31685	\u0120Infinite
31686	Finding
31687	cart
31688	\u0120oy
31689	\u0120RX
31690	aber
31691	\u01201923
31692	\u0120discredited
31693	\u0120strapped
31694	\u0120partnering
31695	\u0120Sang
31696	scope
31697	\u0120Demand
31698	\u0120merging
31699	\u0120overcoming
31700	\u0120drilled
31701	\u0120latitude
31702	Market
31703	\u0120REL
31704	\u0120rescind
31705	\u0120pesticide
31706	],\xe2\u0122\u013f
31707	ERO
31708	\u0120Aristotle
31709	\u0120Flex
31710	\u0120unavoid
31711	\u0120disple
31712	\u0120ambush
31713	\u0120Devon
31714	\u0120Combined
31715	\u0120perennial
31716	\u0120delt
31717	\u0120anatomy
31718	given
31719	\u0120dir
31720	\u0120steroids
31721	\u0120Hz
31722	OPA
31723	\u0120thicker
31724	\u0120distractions
31725	chemical
31726	\u0120Wolverine
31727	either
31728	\u0120Kier
31729	\u0120progressively
31730	\u0120Sinn
31731	\u0120BYU
31732	Tes
31733	apa
31734	\u0120unab
31735	\u0120gradient
31736	\u0120kickoff
31737	\u0120Mavericks
31738	\u0120estimation
31739	\u0120Shields
31740	ansk
31741	\u0120Melania
31742	\u0120CRE
31743	\u0120Morton
31744	iffany
31745	hov
31746	\u0120fetish
31747	\u0120Omaha
31748	\u0120chatter
31749	\u0120busiest
31750	\u0120freezer
31751	\u0120Conrad
31752	ikhail
31753	ilian
31754	\u0120medically
31755	\u0120Renault
31756	\xd9\u012a
31757	olate
31758	\u0120recalling
31759	Multiple
31760	\u0120Scorp
31761	\u0120drying
31762	owment
31763	\u0120Rim
31764	\u0120Levine
31765	\u0120coloring
31766	Dun
31767	\u0120messenger
31768	\u0120crusade
31769	\u0120Offensive
31770	\u0120duct
31771	deen
31772	WN
31773	\u0120Truck
31774	\u0120Casino
31775	\u0120Lieberman
31776	\u0120Ike
31777	\u0120na\xc3\xaf
31778	ircraft
31779	\u0120Killing
31780	clad
31781	\u0120Catalonia
31782	\u0120fulfil
31783	dinand
31784	Va
31785	stakes
31786	\u0120Teresa
31787	\u0120lurking
31788	\u0120proletariat
31789	\u0120softer
31790	\u0120attained
31791	\u0120Reef
31792	\u0120Carrier
31793	ueless
31794	\u0120boxer
31795	\u0120hides
31796	\u0120pregnancies
31797	\u0120Advoc
31798	\u0120chants
31799	\u0120Colleg
31800	\u0120Caf
31801	\u0120prayed
31802	\u0120Nottingham
31803	\u0120Origins
31804	\u0120escapes
31805	\u0120Piper
31806	\u0120replication
31807	\u0120Bench
31808	\u0120apologise
31809	\u0120Movies
31810	\u0120Teddy
31811	Program
31812	\u0120civ
31813	osal
31814	\u0120Kaf
31815	ruck
31816	\xc5\xa3
31817	Franc
31818	380
31819	EPA
31820	lund
31821	\u0120reap
31822	\u0120Ricardo
31823	\u0120lasers
31824	\u0120likened
31825	\u0120Predators
31826	\u0120untouched
31827	\u0120Yanukovych
31828	\u0120Package
31829	\u0120Fifty
31830	\u0120Fahren
31831	\u0120Sisters
31832	\u0120Casc
31833	\u0120coats
31834	\u0120\xd0\xb1
31835	\u0120Pandora
31836	Conservative
31837	Les
31838	\u0120Wester
31839	\u0120Lily
31840	\u0120relinqu
31841	ussian
31842	\u0120seminal
31843	birds
31844	\u0120Programme
31845	\u0120portraying
31846	\u0120bumps
31847	\u0120rag
31848	machine
31849	\u0120Fruit
31850	\u0120Nile
31851	\u0120Banner
31852	\u0120sensing
31853	\u0120Values
31854	\u0120polyg
31855	Got
31856	eny
31857	\u0120Yoga
31858	\xe3\u0122\u012e
31859	\u0120Cummings
31860	ATOR
31861	\u0120Clarkson
31862	\u0120blasting
31863	\u0120transist
31864	\u0120murky
31865	illian
31866	awatts
31867	\u0120darkest
31868	\u0120Pompe
31869	jay
31870	\u0120looting
31871	\u0120chanted
31872	\u0120Howe
31873	\xc3\u012b
31874	\u0120dich
31875	\u0120Philippe
31876	\u0120Kendall
31877	jav
31878	\u0120shady
31879	\u0120teased
31880	acas
31881	ivision
31882	\u0120leveled
31883	tyard
31884	\u0120ze
31885	\u0120Applications
31886	FBI
31887	odder
31888	\u0120aerospace
31889	\u0120hectares
31890	((
31891	Books
31892	\u0120Orchestra
31893	\u0120lax
31894	\u0120sturdy
31895	embed
31896	\u0120patented
31897	\u0120padding
31898	\u0120quotas
31899	\u0120Lobby
31900	\u0120Deborah
31901	ilant
31902	\u0120pee
31903	fork
31904	\u0120commuter
31905	\u0120tyres
31906	\u0120Activity
31907	Complete
31908	\u0120intervening
31909	MON
31910	\u0120AMA
31911	\u0120CrossRef
31912	Companies
31913	\u0120bending
31914	\u0120Sears
31915	thro
31916	\u0120secession
31917	\u0120persists
31918	\u0120mythical
31919	\u0120pg
31920	\u0120CG
31921	\u0120DPS
31922	ampires
31923	\u0120Honestly
31924	[]
31925	\u0120Caps
31926	\u0120cruiser
31927	civil
31928	wrote
31929	armac
31930	Playing
31931	\u0120cane
31932	\u0120phony
31933	\u0120crest
31934	\u0120weld
31935	\u0120CDs
31936	\u0120boon
31937	\u0120downfall
31938	history
31939	\u0120notwithstanding
31940	\u0120purportedly
31941	\u0120domestically
31942	\u0120Tina
31943	thus
31944	\u0120compounded
31945	happy
31946	\u0120Boom
31947	orb
31948	whose
31949	formerly
31950	\u0120Scripture
31951	\u0120Dug
31952	\u0120Convers
31953	\u0120chaired
31954	\u0120aiding
31955	\u0120Leigh
31956	\u0120Shift
31957	\u0120respecting
31958	\u0120sampled
31959	\u0120crab
31960	vana
31961	\u0120Boo
31962	\u0120rods
31963	\u0120slashing
31964	\u0120bolts
31965	isations
31966	\u0120giveaway
31967	\u0120Debt
31968	\u0120dismantling
31969	\u0120antics
31970	\u0120republican
31971	\u0120Kendrick
31972	\u0120Nunes
31973	iona
31974	\u0120YPG
31975	\u0120Dynasty
31976	!]
31977	\u0120waging
31978	\u01201927
31979	asia
31980	\u0120cland
31981	ologue
31982	\u0120shortcuts
31983	\u0120containment
31984	\u0120disclaim
31985	\u0120moderator
31986	pocket
31987	icio
31988	\u0120symbolism
31989	\u0120DRM
31990	Ware
31991	\xd9\u0129
31992	\u0120mu
31993	\u0120Piet
31994	\u0120('
31995	\u0120overflow
31996	metal
31997	ancock
31998	<|endoftext|>
31999	<|pad|>
```

## Full Run Appendix: Last 1000 Merges
- Source: `artifacts/tokenizer/exports/tokenizer_owt32k_full_25m_20260301_061344/merges.txt`
- Merge ranks included: `30743` through `31742`

```text
30743	ĠBern stein
30744	Ġpill ow
30745	Ġmultip ly
30746	Ġshr ine
30747	ĠT et
30748	Ġartic ulated
30749	ĠNord ic
30750	Ġinf initely
30751	13 8
30752	Ġc akes
30753	lect ions
30754	Ġdem ocracies
30755	Ġun heard
30756	charg ing
30757	w ives
30758	ĠP arent
30759	Ġex ited
30760	Ġdef y
30761	Ġdeg ener
30762	ĠSab ha
30763	Ġj ava
30764	urs ed
30765	pir ing
30766	ĠR EST
30767	ĠTr ay
30768	ĠON LY
30769	ĠKing ston
30770	Ġinf ield
30771	aff le
30772	................ ................
30773	Ġprivat ization
30774	Ġl ia
30775	Ġre charge
30776	Ġg ust
30777	ĠBow man
30778	IF F
30779	Ġdivid end
30780	Ġst umble
30781	ĠSp ons
30782	Ġhun ted
30783	Ġg a
30784	pl ot
30785	Ġsuper visors
30786	ĠIr vine
30787	f rey
30788	ond ing
30789	ĠÃ ¤
30790	Ġsucceed ing
30791	Ġintox icated
30792	Ġdispers ed
30793	ĠMy SQL
30794	h ate
30795	Ġen sh
30796	ĠAll ies
30797	Ġlegal izing
30798	Ġfulfill ment
30799	ĠN atalie
30800	ĠMonst ers
30801	an ie
30802	oms ky
30803	ĠSupp ly
30804	Inst all
30805	Ġhass le
30806	Ġprofit ability
30807	) {
30808	R eb
30809	ĠJ D
30810	Ġsm ashing
30811	Ġhor ribly
30812	Ġ` `
30813	mem bers
30814	Ġmen ace
30815	s in
30816	ĠT ED
30817	est ation
30818	In itially
30819	Ġchim panz
30820	Ġap ocalypse
30821	Off icial
30822	ĠNich olson
30823	Ġhandc uffed
30824	Ġtimet able
30825	ĠH iggins
30826	Ġback log
30827	ĠPl ains
30828	Ġconcer ted
30829	ĠZomb ie
30830	ĠM akes
30831	Ġsp heres
30832	Ġsol icit
30833	ĠDa esh
30834	Ġcouncill ors
30835	Ġsc enery
30836	Ġmor p
30837	ĠChron icles
30838	Ġstain less
30839	20 1
30840	+ .
30841	Ġbrilliant ly
30842	an za
30843	Ġdomin ates
30844	Ġfort ress
30845	Ġtermin als
30846	p ick
30847	ĠP ump
30848	Ġhum orous
30849	ĠMay weather
30850	ĠBur r
30851	Ġinflic t
30852	Ġtechn icians
30853	ĠGraph ics
30854	os ate
30855	Ġcomfort ing
30856	Ġ ..........
30857	ĠM afia
30858	Ġstew ards
30859	ĠMahar ashtra
30860	US D
30861	Ġkn ot
30862	Ġseism ic
30863	s ound
30864	ĠC FL
30865	Ġbul bs
30866	Ġde pl
30867	Ġch ast
30868	apt ic
30869	en v
30870	Ġdis illusion
30871	amp hetamine
30872	c ars
30873	Ġa venue
30874	ĠS le
30875	ĠP au
30876	ĠMillenn ium
30877	Ġenz ymes
30878	ĠAr bor
30879	ĠPort al
30880	Conf ig
30881	ear ance
30882	ĠZ erg
30883	whel ming
30884	B razil
30885	Ġ13 7
30886	ĠParliament ary
30887	terror ist
30888	n ov
30889	14 1
30890	ĠEn ough
30891	Ġcul inary
30892	ÄŁ an
30893	Ġredevelop ment
30894	Ġpoison ous
30895	Secret ary
30896	l oid
30897	ĠRec ession
30898	ĠSHA RES
30899	v m
30900	ops is
30901	Ġb um
30902	ast ical
30903	## #
30904	Ġrecount s
30905	Ġmin er
30906	ĠCap itals
30907	ĠReg ular
30908	ĠSound ers
30909	Ġund efeated
30910	ĠKap lan
30911	Ġcl amp
30912	Ġiss u
30913	Ġball park
30914	Ġalt ru
30915	ĠShar if
30916	ĠVent ures
30917	ĠR ousse
30918	PR O
30919	S wed
30920	ist as
30921	Ġgr am
30922	en burg
30923	ĠF ashion
30924	ĠP ett
30925	Ġ4 80
30926	Ġenc ro
30927	ĠBy z
30928	ĠBern anke
30929	rup al
30930	ĠLot us
30931	fore station
30932	ob ar
30933	Ġcream y
30934	Ġm ating
30935	Ġen umer
30936	Ġaff irmed
30937	ĠPip eline
30938	b row
30939	ĠNich ols
30940	ĠSh arma
30941	Ġbenef iting
30942	ĠBo ise
30943	ĠW en
30944	Ġelev ate
30945	Ġoverc rowd
30946	ĠHast ings
30947	Ġun thinkable
30948	Ġune asy
30949	Ġs outheastern
30950	ĠN ept
30951	ĠEs sex
30952	up date
30953	AR R
30954	Ġcool est
30955	Ġout per
30956	Ġconven ed
30957	ĠB org
30958	Ġfun n
30959	at cher
30960	Ġintr usion
30961	or rh
30962	Ġsk ipping
30963	Ġ13 8
30964	Ġdead liest
30965	Ġstir red
30966	ĠBent ley
30967	ĠW ah
30968	Ġdown hill
30969	cl ipse
30970	Ġcivil izations
30971	Ġground work
30972	Ġupset ting
30973	Ġdefic iencies
30974	Ġc d
30975	Ġc itations
30976	pl ays
30977	Ġdismiss ing
30978	Ġcler ic
30979	Ġconstrain t
30980	ĠCont ribut
30981	imm ers
30982	Ġconsolid ated
30983	Ġlav ish
30984	ru ly
30985	ĠPist ons
30986	ĠVander bilt
30987	ra pping
30988	Ġbatt alion
30989	ĠDex ter
30990	T arget
30991	Ġsa p
30992	ĠCl o
30993	Ġwel comes
30994	Ġincre ment
30995	Ġve ctors
30996	Ġyouth ful
30997	D ie
30998	Ġd ams
30999	ident al
31000	Ġcorner stone
31001	viol ence
31002	Ġinconven ience
31003	Ġquant ify
31004	Ġnarrow ed
31005	Charl ie
31006	v ig
31007	res ult
31008	Ġsl ows
31009	Ġdiscrep ancy
31010	ĠS utton
31011	Ġs aint
31012	Ġsh ines
31013	Ġtrans itional
31014	ĠCl ause
31015	?? ?
31016	Ġref urb
31017	S eries
31018	Ġo zone
31019	Ġl ymph
31020	Ġre pr
31021	|> [
31022	M G
31023	ĠD SL
31024	Ġmen stru
31025	ĠRes idents
31026	Ġad ept
31027	ĠFranc ois
31028	Ġoff end
31029	Ġav atar
31030	Ġfree ing
31031	pro claimed
31032	ĠBur lington
31033	ad ena
31034	n umbered
31035	av our
31036	Ġind ifferent
31037	ĠMost ly
31038	test ing
31039	guy en
31040	A U
31041	ag rams
31042	Ġsp ar
31043	z sche
31044	ind al
31045	Ġph on
31046	ĠGl ory
31047	J eremy
31048	i ples
31049	at lantic
31050	ĠP f
31051	Ġprec autions
31052	Ġswe lling
31053	Ġhypothes es
31054	F ord
31055	ĠE lf
31056	ge ons
31057	Ġreg eneration
31058	ĠF ang
31059	Ġwar p
31060	Ġtechn ician
31061	ich ick
31062	be gin
31063	Ġbrill iance
31064	Ġscr ambled
31065	opp able
31066	Ġindef inite
31067	Ġnood les
31068	t tle
31069	he llo
31070	Ġse wer
31071	14 7
31072	Ġvert ically
31073	ĠUb isoft
31074	Ġspray ed
31075	J ess
31076	x i
31077	Ġal oud
31078	ĠO EM
31079	ure rs
31080	ĠPl ans
31081	ig ans
31082	Ġrec onnaissance
31083	ĠAl buquerque
31084	Ġfra ught
31085	ern o
31086	Ġcool ed
31087	Ġ Í
31088	H om
31089	Ġ13 1
31090	D om
31091	ĠThe ft
31092	ste en
31093	ĠCollect ive
31094	H alf
31095	az ard
31096	Ġ. /
31097	ĠDesign er
31098	Ġ13 4
31099	ĠGr ill
31100	Ġhur ricanes
31101	) }
31102	ĠP ratt
31103	ĠR ED
31104	ĠTh ames
31105	Ġtar iff
31106	ĠH ak
31107	Ġv odka
31108	Ġdecl arations
31109	Ġspark ing
31110	ĠM ON
31111	Ġcom o
31112	op ian
31113	ĠV W
31114	Ġlecture r
31115	Ġcaval ry
31116	Ġst if
31117	ĠB iblical
31118	Ġrun away
31119	pr on
31120	Ġcame o
31121	Ġtrust worthy
31122	Ġcomprom ises
31123	ĠPl at
31124	ĠEn emy
31125	Ġfool ed
31126	Ġtum ult
31127	Ġsalv age
31128	ĠP erman
31129	Ġdefault s
31130	ĠPhot ography
31131	ĠSong s
31132	Ġnon partisan
31133	ĠLove craft
31134	A part
31135	ĠCh ick
31136	Ġpos itives
31137	hy dro
31138	ump y
31139	ĠCom par
31140	Ġlist ens
31141	Ġfav oured
31142	ou f
31143	ĠAl to
31144	Ġtor so
31145	Ġcalm ly
31146	ĠF ior
31147	F it
31148	Ġhy giene
31149	E nergy
31150	ĠC i
31151	Ġdep osition
31152	Ġocc ult
31153	ol in
31154	Ġ19 25
31155	Ġens ued
31156	add ock
31157	Ġoutfield er
31158	st asy
31159	ĠLegend ary
31160	it ud
31161	Ġestabl ishes
31162	Ġdis qual
31163	* .
31164	W ord
31165	Ġv ested
31166	Ġsl ips
31167	ĠS emin
31168	ĠD AY
31169	Ġbl and
31170	Ġfinal ists
31171	ĠBo at
31172	Ġgra veyard
31173	Ġqual ifier
31174	ÑĢ Ðµ
31175	Sim on
31176	ĠB orders
31177	OT US
31178	ĠMind s
31179	ĠTur bo
31180	Bre xit
31181	ĠO PS
31182	Ġnom inate
31183	tes que
31184	ĠThe odore
31185	cer y
31186	Ġamen ities
31187	j iang
31188	s list
31189	ĠA by
31190	ĠP ike
31191	ĠMar vin
31192	ĠWood y
31193	ĠOl ive
31194	In itial
31195	ĠEuro s
31196	ĠEven ing
31197	ĠMer rill
31198	Res idents
31199	hett i
31200	Ġgo ats
31201	ape go
31202	ĠOp inion
31203	Ġancest ral
31204	o irs
31205	u o
31206	Ġen riched
31207	ĠSl av
31208	ĠIsa iah
31209	ĠFran Ã§
31210	Ġe uth
31211	aur a
31212	Ġfract ure
31213	ĠG ins
31214	com ments
31215	Ġrevers ing
31216	Ġmid way
31217	ĠVar iety
31218	p oor
31219	r andom
31220	Ġf res
31221	Ġas cent
31222	ph ot
31223	âĢ¦ <|
31224	Ġpress es
31225	ER C
31226	cro ft
31227	cer t
31228	Ġshort fall
31229	pert ure
31230	IC T
31231	ĠLeon ardo
31232	ispens able
31233	Ġt ainted
31234	ind ependent
31235	idd y
31236	Ġcompl icit
31237	auth ored
31238	Ġse gregated
31239	Ġcondition ed
31240	Ġdist ressed
31241	Ġuns igned
31242	Ġded uctions
31243	ĠProgram ming
31244	ĠSE AL
31245	Ġredes igned
31246	Ġgl itch
31247	sc ars
31248	Ġpersecut ed
31249	aby tes
31250	Ġremed ies
31251	Ġn m
31252	Ġav al
31253	E AR
31254	Ġplay ful
31255	sh op
31256	* ,
31257	Ġhar ming
31258	ĠSun shine
31259	ĠGib bs
31260	Ġun res
31261	ah i
31262	ĠC yn
31263	end on
31264	ĠTer ran
31265	Ġcompos itions
31266	Ġhumili ating
31267	ĠChe ss
31268	g re
31269	Ġsing ers
31270	iling ual
31271	Ġreprodu ced
31272	ĠBol ivia
31273	Per malink
31274	Ġarchae ologists
31275	Ġecl ips
31276	... )
31277	Ġfre aking
31278	Ġhub s
31279	Ġempower ment
31280	ĠSuz uki
31281	n one
31282	ĠAn field
31283	A X
31284	ĠPl atinum
31285	Ġself ie
31286	Ġendorse ments
31287	M anchester
31288	r m
31289	Ġdelight ful
31290	commun ication
31291	C I
31292	Ġvit amins
31293	ĠP LAY
31294	Ġexhaust ion
31295	ach a
31296	Ġetern ity
31297	x c
31298	Ġtransl ating
31299	Ġconfidential ity
31300	O bs
31301	c ards
31302	Ġpre ach
31303	ĠCo ke
31304	Ġtra vers
31305	Pro bably
31306	Ġin active
31307	ĠS ew
31308	Ġpe asant
31309	c ss
31310	Ġdur ability
31311	Ġreg ained
31312	T ravel
31313	assad ors
31314	ĠU d
31315	Ġdisc ard
31316	es on
31317	ĠH ale
31318	Ġmay ors
31319	Ġmis led
31320	Ġoffensive ly
31321	OD E
31322	gal itarian
31323	ĠCed ar
31324	Dis ney
31325	Ġm ural
31326	ĠInter cept
31327	ĠK ling
31328	ĠMar ian
31329	Ġrev olutions
31330	Ġcal orie
31331	op ening
31332	Ġgu bernatorial
31333	Pro s
31334	ĠSl ack
31335	ĠGN OME
31336	ĠC omet
31337	Ġ( );
31338	Ġmod ifying
31339	Ġde hyd
31340	ald i
31341	ĠRail road
31342	Ã ¦
31343	ograph s
31344	ĠVe ga
31345	14 8
31346	Ġcom a
31347	Ġstead fast
31348	Ġsubscript ions
31349	Ġforce fully
31350	Ġhar bour
31351	ĠFant astic
31352	ĠMethod s
31353	al an
31354	ĠB illion
31355	Ġsal ute
31356	Ġguard ing
31357	Ġunve il
31358	A verage
31359	Ġgreet ing
31360	F all
31361	ĠU nt
31362	ble y
31363	Ġcomp iling
31364	ract ions
31365	Ġcop ing
31366	ĠIslam abad
31367	rid ges
31368	C ook
31369	Ġbe wild
31370	ĠO B
31371	con ference
31372	Ġprosecut ing
31373	Ġannex ation
31374	Ġrest raining
31375	Ġclo ak
31376	w olves
31377	Ġrepe aling
31378	hett o
31379	ĠPaul a
31380	' ]
31381	Ġpo inters
31382	ĠBl vd
31383	Ġparam ount
31384	Ġconsolid ate
31385	Ac ross
31386	Ġfuzz y
31387	ĠTayy ip
31388	H ack
31389	ok i
31390	ĠSh oot
31391	Ġmanage able
31392	Ġsole mn
31393	Ġgrocer ies
31394	Ġconvey ed
31395	Ġepile psy
31396	Ġun att
31397	Ġwid get
31398	ĠK auf
31399	ili ary
31400	L en
31401	ĠK nown
31402	ĠBab ylon
31403	ĠSupp orters
31404	Ġscratch ing
31405	ĠAsh ton
31406	S ov
31407	he my
31408	ĠK ry
31409	ĠPro secutor
31410	Ġbeh aving
31411	Ġsqu ash
31412	ĠW itt
31413	n ails
31414	Ġprom o
31415	inf lamm
31416	Ġen closed
31417	ĠSh ooting
31418	Ġbill board
31419	RE AK
31420	ut an
31421	ĠD addy
31422	Ġun wit
31423	ield ing
31424	Ġsand box
31425	ous and
31426	f ing
31427	ĠC ertain
31428	ci pled
31429	gg les
31430	ĠInf inite
31431	F inding
31432	c art
31433	Ġo y
31434	ĠR X
31435	ab er
31436	Ġ19 23
31437	Ġdisc redited
31438	Ġstra pped
31439	Ġpartner ing
31440	ĠS ang
31441	sc ope
31442	ĠDem and
31443	Ġmer ging
31444	Ġover coming
31445	Ġdr illed
31446	Ġlat itude
31447	Mark et
31448	ĠR EL
31449	Ġresc ind
31450	Ġpestic ide
31451	] ,âĢĿ
31452	ER O
31453	ĠArist otle
31454	ĠF lex
31455	Ġun avoid
31456	Ġdis ple
31457	Ġamb ush
31458	ĠDev on
31459	ĠComb ined
31460	Ġperenn ial
31461	Ġde lt
31462	Ġanat omy
31463	g iven
31464	Ġd ir
31465	Ġst eroids
31466	ĠH z
31467	OP A
31468	Ġthick er
31469	Ġdistract ions
31470	chem ical
31471	ĠWolver ine
31472	e ither
31473	ĠK ier
31474	Ġprogress ively
31475	ĠS inn
31476	ĠBY U
31477	T es
31478	ap a
31479	Ġun ab
31480	Ġgrad ient
31481	Ġkick off
31482	ĠMaver icks
31483	Ġestim ation
31484	ĠShield s
31485	ans k
31486	ĠMel ania
31487	ĠC RE
31488	ĠMort on
31489	iff any
31490	h ov
31491	Ġfet ish
31492	ĠOm aha
31493	Ġchat ter
31494	Ġbus iest
31495	Ġfree zer
31496	ĠCon rad
31497	ikh ail
31498	il ian
31499	Ġmed ically
31500	ĠRen ault
31501	Ù Ī
31502	ol ate
31503	Ġrecall ing
31504	Mult iple
31505	ĠSc orp
31506	Ġdry ing
31507	ow ment
31508	ĠR im
31509	ĠLev ine
31510	Ġcol oring
31511	D un
31512	Ġmess enger
31513	Ġcrus ade
31514	ĠOff ensive
31515	Ġd uct
31516	de en
31517	W N
31518	ĠTru ck
31519	ĠCas ino
31520	ĠLie berman
31521	ĠI ke
31522	Ġna Ã¯
31523	irc raft
31524	ĠK illing
31525	cl ad
31526	ĠCatal onia
31527	Ġfulf il
31528	din and
31529	V a
31530	st akes
31531	ĠTe resa
31532	Ġlur king
31533	Ġprolet ariat
31534	Ġso fter
31535	Ġatt ained
31536	ĠRe ef
31537	ĠCar rier
31538	uel ess
31539	Ġbox er
31540	Ġh ides
31541	Ġpregn ancies
31542	ĠAdv oc
31543	Ġch ants
31544	ĠCol leg
31545	ĠC af
31546	Ġpr ayed
31547	ĠNot tingham
31548	ĠOrig ins
31549	Ġesc apes
31550	ĠPi per
31551	Ġrepl ication
31552	ĠBen ch
31553	Ġapolog ise
31554	ĠMov ies
31555	ĠT eddy
31556	Pro gram
31557	Ġc iv
31558	os al
31559	ĠK af
31560	ru ck
31561	Å £
31562	Fr anc
31563	3 80
31564	E PA
31565	l und
31566	Ġre ap
31567	ĠRic ardo
31568	Ġlas ers
31569	Ġlik ened
31570	ĠPred ators
31571	Ġunt ouched
31572	ĠYanuk ovych
31573	ĠPack age
31574	ĠFif ty
31575	ĠFah ren
31576	ĠS isters
31577	ĠC asc
31578	Ġco ats
31579	ĠÐ ±
31580	ĠPand ora
31581	Cons ervative
31582	L es
31583	ĠW ester
31584	ĠL ily
31585	Ġrel inqu
31586	uss ian
31587	Ġsemin al
31588	b irds
31589	ĠProgram me
31590	Ġportray ing
31591	Ġbump s
31592	Ġr ag
31593	m achine
31594	ĠF ruit
31595	ĠN ile
31596	ĠBan ner
31597	Ġsens ing
31598	ĠVal ues
31599	Ġpoly g
31600	G ot
31601	en y
31602	ĠY oga
31603	ãĢ Į
31604	ĠCumm ings
31605	AT OR
31606	ĠClarks on
31607	Ġbl asting
31608	Ġtrans ist
31609	Ġmur ky
31610	ill ian
31611	aw atts
31612	Ġdark est
31613	ĠPom pe
31614	j ay
31615	Ġl ooting
31616	Ġch anted
31617	ĠHow e
31618	Ã ī
31619	Ġd ich
31620	ĠPhilipp e
31621	ĠKend all
31622	j av
31623	Ġsh ady
31624	Ġte ased
31625	ac as
31626	iv ision
31627	Ġlevel ed
31628	ty ard
31629	Ġz e
31630	ĠApp lications
31631	F BI
31632	od der
31633	Ġaer ospace
31634	Ġhect ares
31635	( (
31636	Book s
31637	ĠOrche stra
31638	Ġl ax
31639	Ġst urdy
31640	em bed
31641	Ġpat ented
31642	Ġpadd ing
31643	Ġquot as
31644	ĠL obby
31645	ĠDebor ah
31646	il ant
31647	Ġpe e
31648	f ork
31649	Ġcomm uter
31650	Ġty res
31651	ĠAct ivity
31652	Com plete
31653	Ġinterven ing
31654	M ON
31655	ĠAM A
31656	ĠCross Ref
31657	Comp anies
31658	Ġb ending
31659	ĠS ears
31660	th ro
31661	Ġsec ession
31662	Ġpers ists
31663	Ġmyth ical
31664	Ġp g
31665	ĠC G
31666	ĠD PS
31667	amp ires
31668	ĠHonest ly
31669	[ ]
31670	ĠC aps
31671	Ġcru iser
31672	c ivil
31673	w rote
31674	arm ac
31675	Pl aying
31676	Ġcan e
31677	Ġph ony
31678	Ġc rest
31679	Ġwe ld
31680	ĠCD s
31681	Ġbo on
31682	Ġdown fall
31683	hist ory
31684	Ġnot withstanding
31685	Ġpurported ly
31686	Ġdomest ically
31687	ĠT ina
31688	th us
31689	Ġcomp ounded
31690	h appy
31691	ĠBo om
31692	or b
31693	wh ose
31694	former ly
31695	ĠScript ure
31696	ĠD ug
31697	ĠCon vers
31698	Ġcha ired
31699	Ġa iding
31700	ĠLe igh
31701	ĠSh ift
31702	Ġrespect ing
31703	Ġsam pled
31704	Ġcr ab
31705	v ana
31706	ĠB oo
31707	Ġro ds
31708	Ġsl ashing
31709	Ġbol ts
31710	is ations
31711	Ġgive away
31712	ĠDeb t
31713	Ġdismant ling
31714	Ġant ics
31715	Ġrepublic an
31716	ĠKend rick
31717	ĠN unes
31718	ion a
31719	ĠY PG
31720	ĠD ynasty
31721	! ]
31722	Ġw aging
31723	Ġ19 27
31724	as ia
31725	Ġcl and
31726	olog ue
31727	Ġshort cuts
31728	Ġcontain ment
31729	Ġdiscl aim
31730	Ġmoder ator
31731	p ocket
31732	ic io
31733	Ġsymbol ism
31734	ĠDR M
31735	W are
31736	Ù ĩ
31737	Ġm u
31738	ĠP iet
31739	Ġ( '
31740	Ġover flow
31741	met al
31742	anc ock
```
