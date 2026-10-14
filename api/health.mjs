// Vercel Node function — no reliance on local disks or long-lived processes.
export function GET() {
  return Response.json({
    ok: true,
    service: "flight-radar",
    runtime: "vercel-serverless",
    offersFeedConfigured: Boolean(process.env.FLIGHT_RADAR_FEED_URL),
    collectionActive: false,
    message: "Flight collections require an approved durable feed. No live ticket prices are fabricated."
  }, {headers:{"Cache-Control":"no-store"}});
}
