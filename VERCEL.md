# Flight Radar on Vercel

## Deploy (GitHub integration)

1. Connect the Vercel account to ChatGPT, or open https://vercel.com/new .
2. Import `aziriel2020/flight-radar-oracle` into a **new Vercel project** (do not reuse Nuvio's Vercel project).
3. Choose **Other** as the Framework Preset; Root Directory = `./`.
4. `vercel.json` sets `outputDirectory=public`, includes static assets, and auto-detects the Node.js functions in `api/`. Keep the build command empty.
5. Deploy. Test `/`, `/api/health`, and `/api/deals`.

Vercel links deployments to pushes to the GitHub branch. This deployment **will not change the existing Nuvio project**.

## What's actually supported

- Public, responsive flight exploration web UI with real Google Flights links, dynamic departure/return dates and European vs long-haul verified deal filtering.
- `/api/health`: serverless health/status endpoint.
- `/api/deals`: **empty until a permitted, durable source of verified deals is configured**; never publishes fake/synthetic fares.
- `flight_radar/`: original Python SQLite engine remains available for a separate worker, **not** run as a persistent process on Vercel.
- The unofficial `fast-flights` provider remains experimental, opt-in and off by default. Vercel is not a guaranteed 24/7 scraper or persistent data store.

### Connect a verified feed

Configure the environment variable `FLIGHT_RADAR_FEED_URL` in **this Vercel project** with a **server-accessible HTTPS** JSON URL. Optional `FLIGHT_RADAR_FEED_TOKEN` adds a server-side Bearer token to the fetch request.

The feed must be either an array of candidate offers or `{"offers":[...]}`. Only candidate entries with:
- `state: "verified"`
- `checked_at` (or `verified_at`) no older than **60 minutes**
- IATA origin and destination, a positive `checked_price_eur` (or `price_eur`)
- `source` other than `DEMO_NON_REEL`

will be shown. Every offer still needs a final check at the airline/booking site. Unverified, stale, or synthetic prices are discarded.

The source feed is not created by deploying the website. For a continuously running deal collector, configure a separate worker or a supported scheduled function **and durable external storage**; SQLite on Vercel Function local disk is not persistent.

## Costs and terms

Vercel's Hobby tier is limited to **personal non-commercial use** under its terms. A commercial flight-deals subscription service requires an appropriate paid Vercel plan. Limits/costs may change; see https://vercel.com/docs/plans/hobby .

Vercel Cron on Hobby runs at most daily; a frequent flight scanner requires other scheduling or a suitable paid plan (see https://vercel.com/docs/cron-jobs/usage-and-pricing). No cron is enabled in the current deployment.

## Security

All Vercel environment variables are server-side. Do not commit API keys, cookies, SSH keys or tokens. There is no public ingestion route, no authentication or payments yet. The site must not claim real-time deals until the source is connected and verified.
