# Digital Commerce Intelligence Hub

A weekly industry intelligence dashboard for Decathlon China digital commerce and e-commerce teams.

GitHub Actions → Python collectors + verified manual sources → Candidate review → Global selection → Thematic digest → HTML Dashboard + Email → GitHub Pages and history archive

## What It Does

The system combines automatic and manual sources to produce:

- 本周行业观察 / Overview
- 国内电商平台 / Platform Intelligence
- AI 业务应用与技术进展 / AI Applications & Technology
- 体育与服装／户外 / Sports, Apparel & Outdoor
- 传统零售 / Retail Innovation

The automatic generation flow selects up to 30 distinct source links across the overview and four sections. Related articles can support a single information point. Editors review the draft before publishing; saved-draft modes preserve the edited content.

## Information Sources

Automatic sources:

- RSS feeds filtered by section.
- Google News searches, with a Bing RSS fallback.
- Official-site and publisher-name queries defined in `config.py` and `intelligence/editorial.py`.

Searches cover the last 7 days first, then widen to 14 days. Availability depends on public access and search indexing.

Manual source:

- `manual_sources/daily_input.md`

Editors supply verified facts, publication dates and direct article links. Independent Overview research currently comes from entries marked `Category: overview`. Source types are unrestricted, with no required WeChat article share.

## Project Structure

```text
.
├── main.py
├── config.py
├── requirements.txt
├── .github/
│   └── workflows/
│       └── daily.yml
├── sources/
│   ├── common.py
│   ├── rss.py
│   ├── google_news.py
│   ├── http_feed.py
│   ├── editorial_policy.py
│   └── manual.py
├── manual_sources/
│   └── daily_input.md
├── intelligence/
│   ├── editorial.py       # Shared rules, product scope and source catalog
│   ├── prompt.py          # Candidate review
│   ├── gemini.py          # Model review and response handling
│   ├── report_quality.py  # Date, quality and duplicate checks
│   ├── selection.py       # Global source selection
│   ├── batches.py         # Batched model calls
│   ├── digest.py          # Thematic synthesis
│   └── overview.py        # Market overview and section summaries
└── output/
    ├── digest.py          # Classification, citations and rendering
    ├── overview.py
    ├── email.py
    ├── html.py
    ├── archive.py
    ├── preview/
    │   ├── data.json
    │   └── index.html
    └── index.html
```

`tests/test_editorial.py` and `docs/editorial_requirements.md` are optional maintenance files. Runtime rules are defined in the Python modules.

## Dashboard Output

The report uses `thematic_digest_v1`, with concrete titles, factual summaries and article citations. Web pages and email share the same classifications and citation rendering.

| REPORT_MODE | Input | Collect sources / call model | Send email | Output |
|---|---|---|---|---|
| `preview` | Manual material and automatic sources | Yes | Yes | Replace draft JSON and preview HTML |
| `deploy_only` | Saved draft JSON | No | No | Update preview HTML |
| `manual_preview` | Saved draft JSON | No | Yes | Update preview HTML |
| `publish` | Reviewed draft JSON | No | Yes | Update formal dashboard and archive |

Draft data: `output/preview/data.json`  
Preview page: `output/preview/index.html`  
Formal dashboard: `output/index.html`

In GitHub Actions, all four modes deploy the entire `output/` directory to GitHub Pages. The preview page is accessible by URL. Only `publish` updates the formal archive.

Email is delivered through Resend and includes HTML content, a plain-text version and a dashboard link.

## GitHub Secrets

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | Model calls in preview mode |
| `EMAIL_API_KEY` | Resend email API key |
| `EMAIL_TO` | Recipient address or addresses |
| `EMAIL_FROM` | Optional sender address permitted by your Resend account |

Keys are read from environment variables or GitHub Secrets. The default sender is Resend's onboarding address.

`deploy_only` renders saved data without model or email credentials.

## Run Locally

Use Python 3.11 and install the dependencies:

```powershell
pip install -r requirements.txt
```

Render the saved draft:

```powershell
$env:REPORT_MODE = "deploy_only"
python main.py
```

Generate and email an automatic draft:

```powershell
$env:REPORT_MODE = "preview"
$env:GEMINI_API_KEY = "your-model-api-key"
$env:EMAIL_API_KEY = "your-resend-api-key"
$env:EMAIL_TO = "recipient@example.com"
$env:EMAIL_FROM = "verified-sender@example.com"
$env:DASHBOARD_BASE_URL = "https://your-account.github.io/digital-commerce-intelligence-hub/"
python main.py
```

Set `REPORT_MODE` explicitly. When omitted, `python main.py` defaults to publish mode.

Local runs write files; GitHub Actions handles Pages deployment. If the optional tests are present, run `python -m unittest discover -s tests -v`.

## GitHub Actions

The current workflow supports manual execution through `workflow_dispatch`.

1. In Settings → Pages, set the deployment source to GitHub Actions.
2. Upload the week's manual material or reviewed draft JSON.
3. Open Actions → Digital Commerce Intelligence Brief → Run workflow.
4. Select the appropriate report_mode from the table above.
5. Review the preview and run publish when the edition is approved.

The workflow commits generated files and deploys the full output directory. Preview URLs are deployed alongside the formal dashboard.

Scheduled execution requires adding a schedule trigger to `.github/workflows/daily.yml`.

## History Archive

Publish mode renders the reviewed draft and saves:

```text
output/index.html
output/archive/YYYY-MM-DD/index.html
output/archive/index.html
output/data/YYYY-MM-DD.json
```

`output/archive/index.html` lists formal editions in reverse date order. GitHub Actions commits history files back to the repository so archived editions remain available across deployments.

