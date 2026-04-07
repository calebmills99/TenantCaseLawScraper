# TenantCaseLawScraper
 California tenant rights case law scraper — CourtListener-first, SQLite-backed, with topic tagging, outcome detection,    and domain-tuned relevance scoring for unpermitted-unit / RSO / landlord-harassment research

  ## LISTEN UP.

  You came here because some landlord rented you a converted garage with no
  certificate of occupancy and now thinks he's entitled to keep your money.
  He is **not**. Sit down. I'm going to explain how this works.

  This is a Python scraper. It crawls California case law for tenant rights
  cases — unpermitted units, RSO violations, rent disgorgement, landlord
  harassment, the whole sorry parade. It puts the results in a SQLite database
  so you can actually find what you're looking for instead of clicking around
  for six hours like a person who doesn't value their own time.

  I don't have time for nonsense and neither do you. Let's go.

  ---

  ## What it does, plainly

  - Pulls cases from **CourtListener**. That's the primary source. It works.
  - Tries **Justia** as a fallback, but only if you ask nicely with
    `--include-justia`. It's slow. I warned you.
  - Tries **Caselaw Access Project** out of habit. Harvard pulled the plug in
    2024. The scraper notices and moves on. So should you.
  - Tags every case with topics. Twenty-one of them. Things like
    `unpermitted_unit`, `rent_disgorgement`, `rso_coverage`. You know.
    The good stuff.
  - Scores each case for relevance so the on-point ones float to the top
    and the contract dispute about a koi pond sinks where it belongs.
  - Detects who won. Tenant, landlord, dismissed, settled. If the opinion
    doesn't say, it says "unknown." Honesty. Try it sometime.

  ---

  ## Setup. Pay attention.

  You need a CourtListener API token. It's **free**. Don't whine.

  ```bash
  # Step 1. Get the token. Go here. Sign up. It takes thirty seconds.
  #   https://www.courtlistener.com/sign-in/

  # Step 2. Install the thing.
  uv sync --extra justia    # or just `uv sync` if you don't want Justia

  # Step 3. Put your token where the scraper can find it.
  cp .env.example .env
  # Now open .env and paste your token. Don't email it to me.

  source .env

  If you see a 403 error, your token is missing or expired. That's not a bug.
  That's you.

  ---
  How to use it

  # Search for one thing.
  uv run python scraper.py --search "unpermitted unit RSO" --after 2020-01-01

  # Run all twelve preset queries. Go make coffee.
  uv run python scraper.py --run-all --after 2018-01-01

  # Find every case that cites Carter v. Cohen.
  uv run python scraper.py --cite "Carter v. Cohen"

  # Find citations for ALL the seed cases.
  uv run python scraper.py --cite-all

  # Tell me what's in the database.
  uv run python scraper.py --report

  # Get your data out.
  uv run python scraper.py --export-json
  uv run python scraper.py --export-csv

  Everything goes into tenant_case_law.db. Re-running a search never
  overwrites good data with bad data — the scoring uses MAX semantics. I built
  it that way because I know what you're like.

  ---
  The seed cases you should already know

  If you're researching unpermitted-unit cases and you don't recognize these
  names, close this README and go read them first. Come back when you're ready.

  ┌─────────────────────────────┬───────────────────────┬──────────────────────────────────────────────────────────┐
  │            Case             │         Cite          │                      Why it matters                      │
  ├─────────────────────────────┼───────────────────────┼──────────────────────────────────────────────────────────┤
  │ Carter v. Cohen             │ 188 Cal.App.4th 1038  │ Rent disgorgement + treble damages + attorney fees on an │
  │                             │ (2010)                │  unpermitted unit. The big one.                          │
  ├─────────────────────────────┼───────────────────────┼──────────────────────────────────────────────────────────┤
  │ North 7th Street Associates │ 7 Cal.App.5th Supp. 1 │ Zero rent obligation. UD dismissed. Tenant gets fees.    │
  │  v. Constante               │  (2016)               │                                                          │
  ├─────────────────────────────┼───────────────────────┼──────────────────────────────────────────────────────────┤
  │ Gruzen v. Henry             │ 84 Cal.App.3d 517     │ The landlord cannot collect rent on an unpermitted unit. │
  │                             │ (1978)                │  Period.                                                 │
  ├─────────────────────────────┼───────────────────────┼──────────────────────────────────────────────────────────┤
  │ Salazar v. Maradeaga        │ 10 Cal.App.4th Supp.  │ RSO relocation required even when the unit is illegal.   │
  │                             │ 1 (1992)              │                                                          │
  ├─────────────────────────────┼───────────────────────┼──────────────────────────────────────────────────────────┤
  │ Combiner v. Swartz          │ 167 Cal.App.4th 1365  │ The landlord cannot wiggle out of the RSO by claiming    │
  │                             │ (2008)                │ you "agreed" to it.                                      │
  └─────────────────────────────┴───────────────────────┴──────────────────────────────────────────────────────────┘

  ---
  A word about Justia

  Justia is opt-in for a reason. Their search endpoint requires a login now,
  so the scraper has to fetch every case page and filter the text itself. That's
  slow. It also used to have a bug where it would keep every case that
  contained the word "unit" — which, in California real-property law, is
  every case. That's been fixed. The filter now requires all non-stopword
  query terms to match, and there's a stub guard that throws out anything
  under 1KB because that's almost certainly a Cloudflare interstitial pretending
  to be an opinion.

  If you turn it on with --include-justia, you'll see a line like:

  [JUS] fetched=240 kept=12 filtered_out=221 stubs=7

  That's the filter working. If kept ever looks suspiciously close to fetched,
  something has regressed and I want to know about it.

  ---
  What's in the box

  scraper.py              # The whole show. ~970 lines. Single file. Deal with it.
  requirements.txt        # For pip people.
  pyproject.toml          # For uv people. We prefer uv people.
  .env.example            # The template. Copy this. Don't commit the real one.
  README.md               # You are here.
  CLAUDE.md               # Notes for the AI assistant. You can ignore it.
  tenant_case_law.db      # The database. Created on first run. Gitignored.

  ---
  Things I do not want to hear

  - "It's not finding any cases." → Did you set CL_API_TOKEN?
  - "Justia isn't working." → Did you uv sync --extra justia?
  - "The database is huge." → It's case law. Of course it is.
  - "Can it scrape Google Scholar?" → No. They'd ban us in an hour.
  - "Why is the score for my case only 0.4?" → Because it's only sort of relevant.
  That's the whole point.

  ---
  License

  Use it. Don't sue anybody with it that doesn't deserve it. And for the love
  of God, read the cases before you cite them.

  Final word

  I built this so people who got pushed around by slumlords could find the law
  that protects them. If that's you — good. Get to work. The cases are out
  there and now you have a flashlight.

  Order. Order in the court.

  — adapted from the bench, with apologies to the actual Honorable Judith Sheindlin, who would never write Python

  ---
