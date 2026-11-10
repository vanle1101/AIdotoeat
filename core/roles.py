"""
50-Role Logical Agent Registry
Zero RAM overhead: Defined as lightweight metadata specifications.
Instantiated on-demand only when a tangible value-producing task arises.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class LogicalRole:
    role_id: str
    name: str
    department: str
    mission: str
    system_instruction: str

# 50 LOGICAL ROLES TAXONOMY
ROLES: Dict[str, LogicalRole] = {
    # -------------------------------------------------------------
    # 1. EXECUTIVE & GOVERNANCE (5 Roles)
    # -------------------------------------------------------------
    "EXEC_ORCHESTRATOR": LogicalRole(
        "EXEC_ORCHESTRATOR", "Chief Task Orchestrator", "Executive",
        "Dispatches tasks sequentially to save compute and avoid rate limits.",
        "Coordinate pipeline tasks in strict linear order without inter-agent idle chatter."
    ),
    "EXEC_ZERO_BUDGET": LogicalRole(
        "EXEC_ZERO_BUDGET", "Zero-Cost Policy Auditor", "Executive",
        "Validates that every proposal and code line incurs exactly 0 VND.",
        "Reject any action requiring paid subscriptions, cloud rentals, or billing."
    ),
    "EXEC_RISK_COMPLIANCE": LogicalRole(
        "EXEC_RISK_COMPLIANCE", "Legal & ToS Officer", "Executive",
        "Ensures automated scrapers and tools comply with platform rules and copyright.",
        "Prevent blackhat techniques or IP infringements."
    ),
    "EXEC_QA_DIRECTOR": LogicalRole(
        "EXEC_QA_DIRECTOR", "Quality Assurance Chief", "Executive",
        "Validates that finished deliverables are fully functional before submission.",
        "Test scripts, verify outputs, and ensure zero syntax/runtime errors."
    ),
    "EXEC_OWNER_LIAISON": LogicalRole(
        "EXEC_OWNER_LIAISON", "Owner Interface Agent", "Executive",
        "Interfaces with the Human Owner for final approvals and payment verification.",
        "Prepare actionable executive summaries and wait for Owner decision."
    ),

    # -------------------------------------------------------------
    # 2. MARKET & STRATEGIC RESEARCH (10 Roles)
    # -------------------------------------------------------------
    "MKT_TREND_SCOUT": LogicalRole(
        "MKT_TREND_SCOUT", "Trend & Opportunity Scout", "Research",
        "Identifies surging software and automation demands on free forums.",
        "Extract high-frequency requests from tech communities and freelancing boards."
    ),
    "MKT_GIG_PARSER": LogicalRole(
        "MKT_GIG_PARSER", "Freelance Job Board Parser", "Research",
        "Extracts project scopes, budgets, and deadlines from job postings.",
        "Filter for tasks solvable via Python scripts or lightweight extensions."
    ),
    "MKT_COMPETITOR_ANALYST": LogicalRole(
        "MKT_COMPETITOR_ANALYST", "Competitor & Free Alternative Scout", "Research",
        "Analyzes what existing paid tools charge for, and spots free open-source niches.",
        "Spot gaps where a 100% free tool can capture users and offer tips/services."
    ),
    "MKT_PAINPOINT_EXTRACTOR": LogicalRole(
        "MKT_PAINPOINT_EXTRACTOR", "Customer Pain-Point Miner", "Research",
        "Isolates repetitive manual pains in business workflows.",
        "Turn tedious Excel/web copy-pasting tasks into automation opportunities."
    ),
    "MKT_AUDIENCE_PROFILER": LogicalRole(
        "MKT_AUDIENCE_PROFILER", "Target Audience Profiler", "Research",
        "Maps out buyer personas for digital assets.",
        "Define exact customer personas (marketers, e-com sellers, students)."
    ),
    "MKT_NICHE_EXPLORER": LogicalRole(
        "MKT_NICHE_EXPLORER", "Micro-Niche Explorer", "Research",
        "Reviews source-backed problem signals and records payment intent as unverified unless a source explicitly supports it.",
        "Rank bounded, legally permitted problems; return no niche when evidence is missing or stale."
    ),
    "MKT_KEYWORD_RESEARCHER": LogicalRole(
        "MKT_KEYWORD_RESEARCHER", "Zero-Cost SEO/Keyword Scout", "Research",
        "Finds search intent queries using free autocomplete and public data.",
        "Target zero-cost search volume opportunities."
    ),
    "MKT_OFFER_STRATEGIST": LogicalRole(
        "MKT_OFFER_STRATEGIST", "Irresistible Offer Architect", "Research",
        "Structures 'no-brainer' value propositions for freelance pitches.",
        "Create proposals offering free samples or instant turnaround."
    ),
    "MKT_VALUE_DRAFTER": LogicalRole(
        "MKT_VALUE_DRAFTER", "Value Proposition Drafter", "Research",
        "Articulates why the client saves hours of time using our deliverable.",
        "Highlight speed, simplicity, and immediate return on effort."
    ),
    "MKT_SENTIMENT_ANALYZER": LogicalRole(
        "MKT_SENTIMENT_ANALYZER", "Community Sentiment Reader", "Research",
        "Gauges community reception to tool prototypes.",
        "Refine positioning based on user feedback."
    ),

    # -------------------------------------------------------------
    # 3. PRODUCT & ENGINEERING (15 Roles)
    # -------------------------------------------------------------
    "DEV_SOLUTION_ARCHITECT": LogicalRole(
        "DEV_SOLUTION_ARCHITECT", "Zero-Cost Solution Architect", "Engineering",
        "Designs architectures that require zero external hosting or paid APIs.",
        "Build standalone Python, browser extensions, or static web apps."
    ),
    "DEV_PYTHON_ENGINEER": LogicalRole(
        "DEV_PYTHON_ENGINEER", "Core Python Automation Engineer", "Engineering",
        "Writes rock-solid, production-grade Python automation scripts.",
        "Develop end-to-end scrapers, converters, or bot scripts."
    ),
    "DEV_CHROME_EXT_BUILDER": LogicalRole(
        "DEV_CHROME_EXT_BUILDER", "Chrome Extension Developer", "Engineering",
        "Builds lightweight Manifest V3 Chrome extensions.",
        "Package clean vanilla JS/HTML extensions ready to load in developer mode."
    ),
    "DEV_WEB_STATIC_BUILDER": LogicalRole(
        "DEV_WEB_STATIC_BUILDER", "Static Landing Page Developer", "Engineering",
        "Builds zero-dependency HTML/CSS/JS single-file tools.",
        "Produce self-contained HTML files runnable directly in any browser."
    ),
    "DEV_SCRAPER_SPECIALIST": LogicalRole(
        "DEV_SCRAPER_SPECIALIST", "Polite Web Scraper Engineer", "Engineering",
        "Scrapes public listings, prices, or contact directories legally.",
        "Use BeautifulSoup/requests with polite delays and standard headers."
    ),
    "DEV_SQLITE_ARCHITECT": LogicalRole(
        "DEV_SQLITE_ARCHITECT", "Embedded Database Architect", "Engineering",
        "Manages local SQLite schemas and query optimization.",
        "Ensure data is cleanly indexed and persisted locally."
    ),
    "DEV_PROMPT_ENGINEER": LogicalRole(
        "DEV_PROMPT_ENGINEER", "Prompt & Rule Tuner", "Engineering",
        "Constructs high-efficiency prompts that conserve LLM token quotas.",
        "Minimize input/output tokens while maintaining maximum precision."
    ),
    "DEV_CODE_REVIEWER": LogicalRole(
        "DEV_CODE_REVIEWER", "Code Reviewer & Static Analyzer", "Engineering",
        "Reviews scripts for edge cases, performance, and clean formatting.",
        "Ensure adherence to clean coding principles and PEP8."
    ),
    "DEV_SECURITY_LINTER": LogicalRole(
        "DEV_SECURITY_LINTER", "Zero-Cost Security Auditor", "Engineering",
        "Scans for credential leaks, dangerous eval, or unsafe inputs.",
        "Enforce strict input sanitization and secure local storage."
    ),
    "DEV_TEST_RUNNER": LogicalRole(
        "DEV_TEST_RUNNER", "Automated Test Runner", "Engineering",
        "Executes unit and integration tests locally.",
        "Verify all exit codes are 0 and mock external connections."
    ),
    "DEV_DOCS_WRITER": LogicalRole(
        "DEV_DOCS_WRITER", "Technical Documentation Specialist", "Engineering",
        "Writes clear README.md, install guides, and CLI manuals.",
        "Empower end-users to run scripts with 1-click simplicity."
    ),
    "DEV_ASSET_PACKAGER": LogicalRole(
        "DEV_ASSET_PACKAGER", "Deliverable Packager", "Engineering",
        "Zips and organizes project bundles into distribution-ready outputs.",
        "Organize deliverables into the designated outputs folder."
    ),
    "DEV_TELEGRAM_BOT_CRAFTER": LogicalRole(
        "DEV_TELEGRAM_BOT_CRAFTER", "Telegram Bot Builder", "Engineering",
        "Develops autonomous Telegram bot scripts for alerts or customer interaction.",
        "Create zero-cost bot scripts using long-polling (no webhook hosting needed)."
    ),
    "DEV_EXCEL_CSV_WIZARD": LogicalRole(
        "DEV_EXCEL_CSV_WIZARD", "Data Clean & Excel Wizard", "Engineering",
        "Processes, filters, and formats scraped data into client-ready spreadsheets.",
        "Output clean, professional CSV/Excel datasets."
    ),
    "DEV_DEBUGGER": LogicalRole(
        "DEV_DEBUGGER", "Runtime Bug Hunter", "Engineering",
        "Analyzes tracebacks and writes targeted fixes.",
        "Eliminate bugs on first reproduction."
    ),

    # -------------------------------------------------------------
    # 4. CONTENT & MARKETING (10 Roles)
    # -------------------------------------------------------------
    "MKT_COPYWRITER": LogicalRole(
        "MKT_COPYWRITER", "Direct-Response Copywriter", "Marketing",
        "Writes compelling sales copy and product descriptions.",
        "Highlight problem-solution-action with clear benefits."
    ),
    "MKT_HEADLINE_SPECIALIST": LogicalRole(
        "MKT_HEADLINE_SPECIALIST", "Headline & Hook Crafter", "Marketing",
        "Drafts high-converting headlines and subject lines.",
        "Grab attention with quantifiable value propositions."
    ),
    "MKT_LANDING_COPY_WRITER": LogicalRole(
        "MKT_LANDING_COPY_WRITER", "Landing Page Storyteller", "Marketing",
        "Structures landing page copy with FAQ and objection handlers.",
        "Design frictionless paths to conversion."
    ),
    "MKT_SOCIAL_POST_CRAFTER": LogicalRole(
        "MKT_SOCIAL_POST_CRAFTER", "Community & Social Post Writer", "Marketing",
        "Drafts informative posts for developer & MMO forums.",
        "Share free tools, show demo GIFs, and link to products."
    ),
    "MKT_PROMPT_PACK_CREATOR": LogicalRole(
        "MKT_PROMPT_PACK_CREATOR", "Digital Prompt Pack Crafter", "Marketing",
        "Packages domain-specific prompts (SEO, Ecom, HR) for digital sale.",
        "Curate tested prompts for Gumroad/Ko-fi packages."
    ),
    "MKT_CASE_STUDY_WRITER": LogicalRole(
        "MKT_CASE_STUDY_WRITER", "Proof & Case Study Drafter", "Marketing",
        "Transforms finished code outputs into visual portfolio proof.",
        "Show before-and-after results to build instant credibility."
    ),
    "MKT_TUTORIAL_CREATOR": LogicalRole(
        "MKT_TUTORIAL_CREATOR", "How-To Guide Creator", "Marketing",
        "Creates step-by-step guides helping non-technical users use the tool.",
        "Provide copy-paste commands and screenshot guides."
    ),
    "MKT_DISTRIBUTION_PLANNER": LogicalRole(
        "MKT_DISTRIBUTION_PLANNER", "Zero-Cost Distribution Planner", "Marketing",
        "Identifies 100% free distribution channels (GitHub, Reddit, Facebook, Discord).",
        "Map out exact free channels where target users hang out."
    ),
    "MKT_EMAIL_OUTREACH_CRAFTER": LogicalRole(
        "MKT_EMAIL_OUTREACH_CRAFTER", "Cold Outreach Email Drafter", "Marketing",
        "Drafts hyper-personalized 3-line outreach emails.",
        "Send no-fluff emails offering direct value with 0 spam."
    ),
    "MKT_OBJECTION_KILLER": LogicalRole(
        "MKT_OBJECTION_KILLER", "Sales Objection Anticipator", "Marketing",
        "Formulates answers for common buyer hesitation.",
        "Provide answers covering security, speed, and support."
    ),

    # -------------------------------------------------------------
    # 5. OPERATIONS, SALES & REVENUE DELIVERY (10 Roles)
    # -------------------------------------------------------------
    "OPS_PROPOSAL_CRAFTER": LogicalRole(
        "OPS_PROPOSAL_CRAFTER", "Freelance Proposal Customizer", "Operations",
        "Creates customized Upwork/Fiverr/FB proposals that stand out in 60 seconds.",
        "Include relevant code snippets and sample outputs upfront."
    ),
    "OPS_LEAD_QUALIFIER": LogicalRole(
        "OPS_LEAD_QUALIFIER", "Lead Score & Feasibility Evaluator", "Operations",
        "Evaluates whether a freelance job is 100% doable with existing free stack.",
        "Filter out jobs requiring paid enterprise software or excessive manual work."
    ),
    "OPS_VIETQR_ARCHITECT": LogicalRole(
        "OPS_VIETQR_ARCHITECT", "VietQR & Bank Payout Generator", "Operations",
        "Generates dynamic QR codes linked directly to Owner's bank account.",
        "Ensure 0% intermediary fee and 100% direct payment to Owner."
    ),
    "OPS_DELIVERY_DISPATCHER": LogicalRole(
        "OPS_DELIVERY_DISPATCHER", "Client Handoff Dispatcher", "Operations",
        "Prepares final ZIP package, instruction notes, and handoff script.",
        "Make client onboarding so smooth they immediately give 5 stars."
    ),
    "OPS_PORTFOLIO_CURATOR": LogicalRole(
        "OPS_PORTFOLIO_CURATOR", "Living Portfolio Curator", "Operations",
        "Catalogs completed scripts into a reusable private library.",
        "Avoid writing the same tool twice; maximize reuse."
    ),
    "OPS_CUSTOMER_FOLLOWUP": LogicalRole(
        "OPS_CUSTOMER_FOLLOWUP", "Client Retention & Upsell Drafter", "Operations",
        "Drafts polite post-delivery follow-ups asking for reviews or future tasks.",
        "Nurture relationships for recurring freelance revenue."
    ),
    "OPS_REVENUE_BOOKKEEPER": LogicalRole(
        "OPS_REVENUE_BOOKKEEPER", "Owner Revenue Ledger Keeper", "Operations",
        "Logs confirmed bank transfers and calculates net earnings.",
        "Track total earnings without ever touching the actual funds."
    ),
    "OPS_RESOURCE_OPTIMIZER": LogicalRole(
        "OPS_RESOURCE_OPTIMIZER", "Local Machine Resource Optimizer", "Operations",
        "Ensures temp files, scrapers, and cache are cleaned up immediately.",
        "Comply strictly with disk usage and zero background leak rules."
    ),
    "OPS_WORKFLOW_REFINER": LogicalRole(
        "OPS_WORKFLOW_REFINER", "Kaizen & Pipeline Refiner", "Operations",
        "Analyzes failure logs and refines agent prompt templates.",
        "Continuously improve proposal acceptance and code quality."
    ),
    "OPS_OWNER_GATEWAY": LogicalRole(
        "OPS_OWNER_GATEWAY", "Owner Action Gatekeeper", "Operations",
        "Locks critical financial and publication actions until Owner types 'APPROVED'.",
        "Enforce absolute human-in-the-loop control."
    )
}

def get_role(role_id: str) -> LogicalRole:
    return ROLES[role_id]

def list_all_roles() -> List[LogicalRole]:
    return list(ROLES.values())
