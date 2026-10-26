"""The curated skeleton of the federal funding ecosystem.

Identity and hierarchy are asserted here by hand. The enrichment agent fills in
details for these nodes but can never add, remove, or re-parent one — which is
what stops a plausible-sounding agency that does not exist from appearing on
the map.

Scope: organizations that fund, invest in, or buy from early-stage companies
spun out of university research. An institute that only runs intramural science
is included where it sits in the hierarchy (NIH's institutes all route through
the same SBIR mechanism, and a tech transfer officer needs to see that), but
pure administrative offices are not.

Row format:
    (id, name, full_name, parent_id, level, sectors, homepage, note)
"""

from __future__ import annotations

from atlas.schema import SeedNode

ROWS: list[tuple] = [
    # --- root ---------------------------------------------------------------
    ("us-gov", "U.S. Federal Government", "United States Federal Government", "", "root",
     ["cross-sector"], "https://www.usa.gov/", "Root of the map."),

    # === HHS ================================================================
    ("hhs", "HHS", "U.S. Department of Health and Human Services", "us-gov", "department",
     ["health", "biotech", "medical-device"], "https://www.hhs.gov/",
     "Largest funder of biomedical research in the world; parent of NIH, BARDA, ARPA-H, FDA, CDC."),

    ("nih", "NIH", "National Institutes of Health", "hhs", "agency",
     ["health", "biotech", "medical-device"], "https://www.nih.gov/",
     "27 institutes and centers. Nearly all small-business funding flows through one shared SBIR/STTR mechanism."),
    ("nih-sbir", "NIH SBIR/STTR", "NIH Small Business Innovation Research / Technology Transfer", "nih", "program",
     ["health", "biotech", "medical-device"], "https://sbir.nih.gov/",
     "The single largest source of non-dilutive funding for health startups. Institutes fund against it from their own budgets."),
    ("nih-seed", "SEED", "NIH Small business Education and Entrepreneurial Development", "nih", "program",
     ["health", "biotech"], "https://seed.nih.gov/",
     "NIH's front door for entrepreneurs; runs the I-Corps and Concept-to-Clinic programs. Best first contact for a new spinout."),
    ("nih-icorps", "NIH I-Corps", "NIH Innovation Corps", "nih-seed", "program",
     ["health", "biotech"], "https://seed.nih.gov/support-for-entrepreneurs/i-corps",
     "Customer-discovery training for SBIR awardees. Non-financial but the usual on-ramp."),
    ("ncats", "NCATS", "National Center for Advancing Translational Sciences", "nih", "agency",
     ["health", "biotech"], "https://ncats.nih.gov/",
     "NIH's translational arm. Funds the de-risking work between discovery and a company."),
    ("nci", "NCI", "National Cancer Institute", "nih", "agency",
     ["health", "biotech"], "https://www.cancer.gov/", "Largest NIH institute; runs its own SBIR Development Center."),
    ("nci-sbir", "NCI SBIR Center", "NCI SBIR Development Center", "nci", "program",
     ["health", "biotech"], "https://sbir.cancer.gov/",
     "Unusually hands-on: runs Investor Initiatives and I-Corps alongside awards."),
    ("niaid", "NIAID", "National Institute of Allergy and Infectious Diseases", "nih", "agency",
     ["health", "biotech"], "https://www.niaid.nih.gov/", "Infectious disease, immunology, vaccines."),
    ("nhlbi", "NHLBI", "National Heart, Lung, and Blood Institute", "nih", "agency",
     ["health", "medical-device"], "https://www.nhlbi.nih.gov/", "Runs SMARTT and other device-translation resources."),
    ("nibib", "NIBIB", "National Institute of Biomedical Imaging and Bioengineering", "nih", "agency",
     ["medical-device", "health"], "https://www.nibib.nih.gov/", "The device and imaging institute; key for medtech spinouts."),
    ("ninds", "NINDS", "National Institute of Neurological Disorders and Stroke", "nih", "agency",
     ["health", "biotech"], "https://www.ninds.nih.gov/", "Neuro; runs translational programs including BPN."),
    ("niddk", "NIDDK", "National Institute of Diabetes and Digestive and Kidney Diseases", "nih", "agency",
     ["health", "biotech"], "https://www.niddk.nih.gov/", "Metabolic, endocrine, renal."),
    ("nia", "NIA", "National Institute on Aging", "nih", "agency",
     ["health", "biotech"], "https://www.nia.nih.gov/", "Alzheimer's funding has grown sharply; large SBIR set-aside."),
    ("nimh", "NIMH", "National Institute of Mental Health", "nih", "agency",
     ["health", "ai-software"], "https://www.nimh.nih.gov/", "Mental health, including digital therapeutics."),
    ("nichd", "NICHD", "Eunice Kennedy Shriver National Institute of Child Health and Human Development", "nih", "agency",
     ["health", "medical-device"], "https://www.nichd.nih.gov/", "Pediatric and maternal health; pediatric device work."),
    ("nida", "NIDA", "National Institute on Drug Abuse", "nih", "agency",
     ["health", "biotech"], "https://nida.nih.gov/", "Substance use; notably active SBIR program."),
    ("niaaa", "NIAAA", "National Institute on Alcohol Abuse and Alcoholism", "nih", "agency",
     ["health"], "https://www.niaaa.nih.gov/", "Alcohol use disorder."),
    ("nei", "NEI", "National Eye Institute", "nih", "agency",
     ["health", "medical-device"], "https://www.nei.nih.gov/", "Vision; strong gene-therapy history."),
    ("nidcd", "NIDCD", "National Institute on Deafness and Other Communication Disorders", "nih", "agency",
     ["health", "medical-device"], "https://www.nidcd.nih.gov/", "Hearing, balance, speech."),
    ("nidcr", "NIDCR", "National Institute of Dental and Craniofacial Research", "nih", "agency",
     ["health"], "https://www.nidcr.nih.gov/", "Dental and craniofacial."),
    ("niehs", "NIEHS", "National Institute of Environmental Health Sciences", "nih", "agency",
     ["health", "environment"], "https://www.niehs.nih.gov/", "Environmental exposure and toxicology."),
    ("nigms", "NIGMS", "National Institute of General Medical Sciences", "nih", "agency",
     ["health", "biotech"], "https://www.nigms.nih.gov/", "Basic science and research tools; strong for platform technologies."),
    ("nimhd", "NIMHD", "National Institute on Minority Health and Health Disparities", "nih", "agency",
     ["health"], "https://www.nimhd.nih.gov/", "Health equity."),
    ("ninr", "NINR", "National Institute of Nursing Research", "nih", "agency",
     ["health"], "https://www.ninr.nih.gov/",
     "Small institute, easy to miss — and the clearest example of why the hierarchy matters: it shares NIH's SBIR mechanism."),
    ("nhgri", "NHGRI", "National Human Genome Research Institute", "nih", "agency",
     ["biotech", "health"], "https://www.genome.gov/", "Genomics and sequencing technology."),
    ("niams", "NIAMS", "National Institute of Arthritis and Musculoskeletal and Skin Diseases", "nih", "agency",
     ["health", "medical-device"], "https://www.niams.nih.gov/", "Musculoskeletal, rheumatology, dermatology."),
    ("nlm", "NLM", "National Library of Medicine", "nih", "agency",
     ["ai-software", "health"], "https://www.nlm.nih.gov/", "Biomedical informatics and health IT."),
    ("nccih", "NCCIH", "National Center for Complementary and Integrative Health", "nih", "agency",
     ["health"], "https://www.nccih.nih.gov/", "Complementary and integrative approaches."),
    ("fic", "FIC", "John E. Fogarty International Center", "nih", "agency",
     ["health"], "https://www.fic.nih.gov/", "Global health research partnerships."),

    ("aspr", "ASPR", "Administration for Strategic Preparedness and Response", "hhs", "agency",
     ["health", "biotech", "security"], "https://aspr.hhs.gov/", "HHS's preparedness arm; parent of BARDA."),
    ("barda", "BARDA", "Biomedical Advanced Research and Development Authority", "aspr", "agency",
     ["health", "biotech", "security"], "https://www.medicalcountermeasures.gov/barda/",
     "Funds medical countermeasures at higher TRL than NIH — the step after a spinout has clinical data."),
    ("barda-drive", "DRIVe", "BARDA Division of Research, Innovation and Ventures", "barda", "program",
     ["health", "biotech"], "https://drive.hhs.gov/",
     "BARDA's early-stage, startup-facing front door, run through a network of Accelerators."),
    ("barda-ventures", "BARDA Ventures", "BARDA Ventures", "barda", "program",
     ["health", "biotech"], "https://drive.hhs.gov/bardaventures.html",
     "Equity-style investment partnership — rare for a federal health agency."),
    ("barda-bioshield", "Project BioShield", "Project BioShield Special Reserve Fund", "barda", "program",
     ["health", "security"], "https://aspr.hhs.gov/", "Advance-purchase commitments for countermeasures."),

    ("arpa-h", "ARPA-H", "Advanced Research Projects Agency for Health", "hhs", "agency",
     ["health", "biotech", "medical-device"], "https://arpa-h.gov/",
     "Created 2022 on the DARPA model. Programme-manager driven, high-risk, large awards."),
    ("arpa-h-openbaa", "ARPA-H Open BAA", "ARPA-H Open Broad Agency Announcement", "arpa-h", "program",
     ["health", "biotech"], "https://arpa-h.gov/engage-and-transition/funding",
     "Rolling, unsolicited route in — unusual and underused by universities."),
    ("arpa-h-patio", "PATIO", "ARPA-H Project Accelerator Transition Innovation Office", "arpa-h", "program",
     ["health", "biotech"], "https://arpa-h.gov/", "Commercial transition support for ARPA-H performers."),

    ("fda", "FDA", "U.S. Food and Drug Administration", "hhs", "agency",
     ["health", "medical-device", "biotech"], "https://www.fda.gov/",
     "Regulator, but also a grant-maker through orphan products and device programs."),
    ("fda-oopd", "Orphan Products Grants", "FDA Office of Orphan Products Development Clinical Trials Grants", "fda", "program",
     ["health", "biotech"], "https://www.fda.gov/industry/developing-products-rare-diseases-conditions",
     "Funds clinical trials for rare disease products — directly relevant to many university spinouts."),
    ("fda-pdc", "Pediatric Devices", "FDA Pediatric Device Consortia Grants Program", "fda", "program",
     ["medical-device", "health"], "https://www.fda.gov/",
     "Funds consortia that in turn support pediatric device developers."),
    ("cdrh-tap", "CDRH TAP", "FDA Total Product Life Cycle Advisory Program", "fda", "program",
     ["medical-device"], "https://www.fda.gov/medical-devices/",
     "Not money — early strategic advice for breakthrough devices. Valuable and widely unknown."),

    ("cdc", "CDC", "Centers for Disease Control and Prevention", "hhs", "agency",
     ["health", "security"], "https://www.cdc.gov/", "Public health; participates in the HHS SBIR programme."),
    ("cdc-sbir", "CDC SBIR", "CDC Small Business Innovation Research Program", "cdc", "program",
     ["health"], "https://www.cdc.gov/", "Small but low-competition relative to NIH."),
    ("ahrq", "AHRQ", "Agency for Healthcare Research and Quality", "hhs", "agency",
     ["health", "ai-software"], "https://www.ahrq.gov/", "Health services research, patient safety, health IT."),
    ("acl", "ACL", "Administration for Community Living", "hhs", "agency",
     ["health", "medical-device"], "https://acl.gov/", "Assistive technology and disability; runs an SBIR programme."),
    ("cms-cmmi", "CMMI", "CMS Center for Medicare and Medicaid Innovation", "hhs", "agency",
     ["health"], "https://www.cms.gov/priorities/innovation/", "Not a grant-maker to startups, but it sets the reimbursement path."),

    # === DEFENSE ============================================================
    ("dod", "Defense", "U.S. Department of Defense", "us-gov", "department",
     ["defense", "security"], "https://www.defense.gov/",
     "Largest SBIR spender in government, spread across many independent commands."),
    ("dod-sbir", "DoD SBIR/STTR", "Department of Defense SBIR/STTR Program", "dod", "program",
     ["defense", "security"], "https://www.dodsbirsttr.mil/",
     "Umbrella for the component programmes; topics are released on a shared cycle."),
    ("darpa", "DARPA", "Defense Advanced Research Projects Agency", "dod", "agency",
     ["defense", "ai-software", "biotech"], "https://www.darpa.mil/",
     "Program-manager driven. The model every other ARPA copies."),
    ("diu", "DIU", "Defense Innovation Unit", "dod", "agency",
     ["defense", "ai-software"], "https://www.diu.mil/",
     "Commercial-first, fast contracting through Other Transaction Authority."),
    ("osc", "OSC", "DoD Office of Strategic Capital", "dod", "agency",
     ["defense", "advanced-manufacturing", "semiconductors"], "https://www.cto.mil/osc/",
     "Loans, not grants — a genuinely new instrument for hardware scale-up."),
    ("afwerx", "AFWERX", "AFWERX, Department of the Air Force Innovation Arm", "dod", "agency",
     ["defense", "space", "ai-software"], "https://afwerx.com/",
     "Runs the Air Force SBIR/STTR with open topics and fast cycles."),
    ("spacewerx", "SpaceWERX", "SpaceWERX, U.S. Space Force Innovation Arm", "afwerx", "program",
     ["space", "defense"], "https://spacewerx.us/", "Space Force counterpart to AFWERX."),
    ("army-xtech", "Army xTech", "U.S. Army xTech Program", "dod", "agency",
     ["defense"], "https://www.xtech.army.mil/", "Prize competitions as an on-ramp to Army SBIR."),
    ("army-sbir", "Army SBIR/STTR", "U.S. Army SBIR/STTR Program", "dod", "program",
     ["defense"], "https://armysbir.army.mil/", "Army component of the DoD programme."),
    ("navy-sbir", "Navy SBIR/STTR", "U.S. Navy SBIR/STTR Program", "dod", "program",
     ["defense"], "https://www.navysbir.com/", "Navy component; strong transition support."),
    ("onr", "ONR", "Office of Naval Research", "dod", "agency",
     ["defense"], "https://www.onr.navy.mil/", "Basic through applied naval research."),
    ("nsin", "NSIN", "National Security Innovation Network", "dod", "agency",
     ["defense", "security"], "https://www.nsin.mil/", "Connects universities and startups to defense problems."),
    ("sofwerx", "SOFWERX", "SOFWERX, U.S. Special Operations Command", "dod", "agency",
     ["defense"], "https://www.sofwerx.org/", "SOCOM's rapid prototyping arm."),
    ("dha", "Defense Health", "Defense Health Agency", "dod", "agency",
     ["health", "defense", "medical-device"], "https://www.health.mil/", "Military health system."),
    ("dha-sbir", "DHA SBIR/STTR", "Defense Health Agency SBIR/STTR Program", "dha", "program",
     ["health", "defense"], "https://www.health.mil/", "Military-relevant health technology."),
    ("usamrdc", "USAMRDC", "U.S. Army Medical Research and Development Command", "dod", "agency",
     ["health", "defense", "medical-device"], "https://mrdc.health.mil/",
     "The army's medical research command; parent of CDMRP and the consortia."),
    ("cdmrp", "CDMRP", "Congressionally Directed Medical Research Programs", "usamrdc", "program",
     ["health", "biotech", "medical-device"], "https://cdmrp.health.mil/",
     "Congressionally earmarked disease programmes. Often overlooked by universities and far less competitive than NIH."),
    ("mtec", "MTEC", "Medical Technology Enterprise Consortium", "usamrdc", "program",
     ["health", "medical-device", "biotech"], "https://mtec-sc.org/",
     "Other Transaction consortium — membership-based, much faster than a grant."),
    ("mcdc", "MCDC", "Medical CBRN Defense Consortium", "usamrdc", "program",
     ["health", "security", "biotech"], "https://medcbrn.org/", "OTA consortium for chem-bio defense medical countermeasures."),

    # === ENERGY =============================================================
    ("doe", "DOE", "U.S. Department of Energy", "us-gov", "department",
     ["energy", "advanced-manufacturing"], "https://www.energy.gov/",
     "Owns the national laboratory system; several distinct commercialization routes."),
    ("arpa-e", "ARPA-E", "Advanced Research Projects Agency – Energy", "doe", "agency",
     ["energy"], "https://arpa-e.energy.gov/", "High-risk energy technology, program-manager driven."),
    ("doe-sbir", "DOE SBIR/STTR", "DOE Office of Science SBIR/STTR Programs", "doe", "program",
     ["energy", "advanced-manufacturing"], "https://science.osti.gov/sbir",
     "Topics are published well ahead of the cycle — unusually plannable."),
    ("doe-ott", "OTT", "DOE Office of Technology Transitions", "doe", "agency",
     ["energy"], "https://www.energy.gov/technologytransitions/",
     "Owns DOE's commercialization strategy and the lab-to-market pipeline."),
    ("leep", "LEEP", "DOE Lab-Embedded Entrepreneurship Program", "doe-ott", "program",
     ["energy", "advanced-manufacturing"], "https://www.energy.gov/eere/lab-embedded-entrepreneurship-program",
     "Fellowships embedding founders inside national labs — Cyclotron Road, Chain Reaction, Innovation Crossroads, West Gate."),
    ("eere", "EERE", "Office of Energy Efficiency and Renewable Energy", "doe", "agency",
     ["energy"], "https://www.energy.gov/eere/", "Applied energy programmes and prize competitions."),
    ("oced", "OCED", "Office of Clean Energy Demonstrations", "doe", "agency",
     ["energy"], "https://www.energy.gov/oced/", "Large-scale first-of-a-kind demonstrations."),
    ("doe-lpo", "Loan Programs", "DOE Loan Programs Office", "doe", "agency",
     ["energy"], "https://www.energy.gov/lpo/", "Debt financing at a scale no grant reaches."),

    # === NSF ================================================================
    ("nsf", "NSF", "National Science Foundation", "us-gov", "department",
     ["cross-sector", "ai-software"], "https://www.nsf.gov/",
     "Funds all non-medical science; the TIP directorate is its commercialization arm."),
    ("nsf-tip", "TIP", "NSF Directorate for Technology, Innovation and Partnerships", "nsf", "agency",
     ["cross-sector"], "https://www.nsf.gov/tip/", "Created 2022; consolidates NSF's translation programmes."),
    ("nsf-seedfund", "NSF Seed Fund", "NSF SBIR/STTR — America's Seed Fund", "nsf-tip", "program",
     ["cross-sector", "ai-software", "advanced-manufacturing"], "https://seedfund.nsf.gov/",
     "Sector-agnostic and founder-friendly; project pitch gives a fast no."),
    ("nsf-icorps", "NSF I-Corps", "NSF Innovation Corps", "nsf-tip", "program",
     ["cross-sector"], "https://new.nsf.gov/funding/initiatives/i-corps",
     "The original customer-discovery programme; the national network runs through university hubs."),
    ("nsf-pfi", "PFI", "NSF Partnerships for Innovation", "nsf-tip", "program",
     ["cross-sector"], "https://new.nsf.gov/funding/opportunities/pfi-partnerships-innovation",
     "Translation funding that goes to the university, not a company — important for pre-spinout work."),
    ("nsf-engines", "Engines", "NSF Regional Innovation Engines", "nsf-tip", "program",
     ["cross-sector"], "https://new.nsf.gov/funding/initiatives/regional-innovation-engines",
     "Very large regional awards; a university is usually a partner rather than a lead."),
    ("nsf-ca", "Convergence Accelerator", "NSF Convergence Accelerator", "nsf-tip", "program",
     ["cross-sector", "ai-software"], "https://new.nsf.gov/funding/initiatives/convergence-accelerator",
     "Cohort-based, use-inspired, with a hard deliverable focus."),

    # === NASA ===============================================================
    ("nasa", "NASA", "National Aeronautics and Space Administration", "us-gov", "department",
     ["space"], "https://www.nasa.gov/", "Space technology, with a strong small-business route."),
    ("nasa-sbir", "NASA SBIR/STTR", "NASA SBIR/STTR Program", "nasa", "program",
     ["space", "advanced-manufacturing"], "https://sbir.nasa.gov/", "Topic-driven; STTR requires a university partner."),
    ("nasa-flight", "Flight Opportunities", "NASA Flight Opportunities Program", "nasa", "program",
     ["space"], "https://www.nasa.gov/directorates/spacetech/flightopportunities/",
     "Buys suborbital flight tests — in-kind rather than cash."),
    ("nasa-t2", "Tech Transfer", "NASA Technology Transfer Program", "nasa", "program",
     ["space"], "https://technology.nasa.gov/", "Licenses NASA patents out; the reverse direction of most of this map."),

    # === COMMERCE ===========================================================
    ("doc", "DOC / Commerce", "U.S. Department of Commerce", "us-gov", "department",
     ["advanced-manufacturing", "semiconductors"], "https://www.commerce.gov/",
     "Parent of NIST, EDA, and NOAA; the department most focused on industrial competitiveness."),
    ("nist", "NIST", "National Institute of Standards and Technology", "doc", "agency",
     ["advanced-manufacturing", "semiconductors"], "https://www.nist.gov/", "Measurement science and standards."),
    ("nist-sbir", "NIST SBIR", "NIST Small Business Innovation Research Program", "nist", "program",
     ["advanced-manufacturing", "semiconductors"], "https://www.nist.gov/tpo/small-business-innovation-research-program",
     "Small programme, tightly scoped to NIST measurement priorities."),
    ("nist-mep", "MEP", "NIST Hollings Manufacturing Extension Partnership", "nist", "program",
     ["advanced-manufacturing"], "https://www.nist.gov/mep", "State-level manufacturing advisory network."),
    ("chips-rd", "CHIPS R&D", "CHIPS Research and Development Office", "nist", "program",
     ["semiconductors"], "https://www.nist.gov/chips", "NSTC and NAPMP; very large semiconductor awards."),
    ("eda", "EDA", "Economic Development Administration", "doc", "agency",
     ["cross-sector"], "https://www.eda.gov/", "Place-based economic development."),
    ("tech-hubs", "Tech Hubs", "EDA Regional Technology and Innovation Hubs", "eda", "program",
     ["cross-sector", "semiconductors"], "https://www.eda.gov/funding/programs/regional-technology-and-innovation-hubs",
     "Consortium awards; universities are usually anchor partners."),
    ("build-to-scale", "Build to Scale", "EDA Build to Scale Program", "eda", "program",
     ["cross-sector"], "https://www.eda.gov/funding/programs/build-to-scale",
     "Funds the accelerators and venture-development organizations themselves — a route a TTO can apply to directly."),
    ("noaa", "NOAA", "National Oceanic and Atmospheric Administration", "doc", "agency",
     ["environment"], "https://www.noaa.gov/", "Ocean, atmosphere, climate."),
    ("noaa-sbir", "NOAA SBIR", "NOAA Small Business Innovation Research Program", "noaa", "program",
     ["environment"], "https://techpartnerships.noaa.gov/sbir/", "Environmental sensing and climate technology."),

    # === DHS ================================================================
    ("dhs", "DHS", "U.S. Department of Homeland Security", "us-gov", "department",
     ["security"], "https://www.dhs.gov/", "Homeland security technology."),
    ("dhs-svip", "SVIP", "DHS Silicon Valley Innovation Program", "dhs", "program",
     ["security", "ai-software"], "https://www.dhs.gov/science-and-technology/svip",
     "Non-dilutive, staged, startup-native contracting."),
    ("dhs-sbir", "DHS SBIR", "DHS Small Business Innovation Research Program", "dhs", "program",
     ["security"], "https://www.dhs.gov/science-and-technology/sbir", "Topic-driven homeland security SBIR."),

    # === USDA ===============================================================
    ("usda", "USDA", "U.S. Department of Agriculture", "us-gov", "department",
     ["agriculture"], "https://www.usda.gov/", "Agriculture, food systems, rural development."),
    ("usda-nifa", "NIFA", "National Institute of Food and Agriculture", "usda", "agency",
     ["agriculture"], "https://www.nifa.usda.gov/", "USDA's extramural research funder."),
    ("usda-sbir", "USDA SBIR/STTR", "USDA SBIR/STTR Program", "usda-nifa", "program",
     ["agriculture", "biotech"], "https://www.nifa.usda.gov/grants/programs/sbir-sttr",
     "Covers ag-biotech and food technology; one application cycle a year."),

    # === TRANSPORTATION =====================================================
    ("dot", "DOT", "U.S. Department of Transportation", "us-gov", "department",
     ["transportation"], "https://www.transportation.gov/", "Surface, air, and rail transportation."),
    ("dot-sbir", "DOT SBIR", "U.S. DOT Small Business Innovation Research Program", "dot", "program",
     ["transportation"], "https://www.transportation.gov/sbir", "Small, topic-driven programme."),
    ("arpa-i", "ARPA-I", "Advanced Research Projects Agency – Infrastructure", "dot", "agency",
     ["transportation"], "https://www.transportation.gov/arpa-i", "Newest ARPA; infrastructure technology."),

    # === EPA / EDUCATION ====================================================
    ("epa", "EPA", "U.S. Environmental Protection Agency", "us-gov", "department",
     ["environment"], "https://www.epa.gov/", "Environmental protection and technology."),
    ("epa-sbir", "EPA SBIR", "EPA Small Business Innovation Research Program", "epa", "program",
     ["environment"], "https://www.epa.gov/sbir", "Clean technology and pollution control."),
    ("ed", "Education", "U.S. Department of Education", "us-gov", "department",
     ["education"], "https://www.ed.gov/", "Education research and technology."),
    ("ies-sbir", "ED/IES SBIR", "Institute of Education Sciences SBIR Program", "ed", "program",
     ["education", "ai-software"], "https://ies.ed.gov/sbir/", "Education technology with an evidence requirement."),

    # === SBA ================================================================
    ("sba", "SBA", "U.S. Small Business Administration", "us-gov", "department",
     ["cross-sector"], "https://www.sba.gov/", "Sets SBIR/STTR policy government-wide; also an investor."),
    ("sbir-framework", "SBIR framework", "SBIR/STTR Government-wide Policy Framework", "sba", "program",
     ["cross-sector"], "https://www.sbir.gov/",
     "The rules every participating agency follows — eligibility, phases, data rights. Read this once and it applies everywhere."),
    ("sbic", "SBIC", "Small Business Investment Company Program", "sba", "program",
     ["cross-sector"], "https://www.sba.gov/funding-programs/investment-capital",
     "Licenses and leverages private funds — federal money reaching startups through VCs."),
    ("sba-gafc", "Growth Accelerators", "SBA Growth Accelerator Fund Competition", "sba", "program",
     ["cross-sector"], "https://www.sba.gov/", "Funds accelerators and support organizations rather than companies."),

    # === INTELLIGENCE + STRATEGIC ===========================================
    ("ic", "IC + strategic", "Intelligence Community and Strategic Investors", "us-gov", "department",
     ["security", "ai-software"], "https://www.intelligence.gov/", "Mission-driven investors outside the normal grant system."),
    ("iarpa", "IARPA", "Intelligence Advanced Research Projects Activity", "ic", "agency",
     ["security", "ai-software"], "https://www.iarpa.gov/", "High-risk intelligence research, program-manager driven."),
    ("inqtel", "In-Q-Tel", "In-Q-Tel", "ic", "agency",
     ["security", "ai-software", "biotech"], "https://www.iqt.org/",
     "Not a federal agency: a non-profit strategic investor funded by the IC. Takes equity."),

    # === TREASURY ===========================================================
    ("treasury", "Treasury", "U.S. Department of the Treasury", "us-gov", "department",
     ["cross-sector"], "https://home.treasury.gov/", "Reaches startups indirectly, through the states."),
    ("ssbci", "SSBCI", "State Small Business Credit Initiative", "treasury", "program",
     ["cross-sector"], "https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci",
     "Federal capital deployed by state venture programmes — the route most university spinouts never hear about."),
]


def _group_of(node_id: str, by_id: dict[str, tuple]) -> str:
    """Walk up to the department under the root; that is the colour cluster."""
    cur = node_id
    while True:
        row = by_id[cur]
        parent = row[3]
        if parent in ("", "us-gov"):
            return cur
        cur = parent


def load_seed() -> list[SeedNode]:
    by_id = {r[0]: r for r in ROWS}
    nodes: list[SeedNode] = []
    for node_id, name, full_name, parent, level, sectors, homepage, note in ROWS:
        nodes.append(
            SeedNode(
                id=node_id,
                name=name,
                full_name=full_name,
                parent_id=parent,
                level=level,
                group="root" if node_id == "us-gov" else _group_of(node_id, by_id),
                sectors=sectors,
                homepage=homepage,
                note=note,
            )
        )
    return nodes


if __name__ == "__main__":
    seed = load_seed()
    ids = [n.id for n in seed]
    assert len(ids) == len(set(ids)), "duplicate id in seed"
    known = set(ids)
    for n in seed:
        assert n.parent_id == "" or n.parent_id in known, f"orphan: {n.id} -> {n.parent_id}"
    print(f"{len(seed)} nodes")
    from collections import Counter
    print("by level:", dict(Counter(n.level for n in seed)))
    print("by group:", dict(Counter(n.group for n in seed)))
