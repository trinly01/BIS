import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getOptions, lookupBenefits } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, Gift, CalendarDays } from "lucide-react"

const inputCls =
  "w-full h-11 rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"

const TYPE_LABEL = {
  calamity_aid: "Calamity Aid", free_medicines: "Free Medicines",
  free_vaccines: "Free Vaccines", financial_assistance: "Financial Assistance",
  food_packs: "Food Packs", scholarship: "Scholarship", other: "Other",
}
const peso = (n) => (n == null ? null : "₱" + Number(n).toLocaleString())

export default function BenefitsPage() {
  const [opts, setOpts] = useState(null)
  const [mobile, setMobile] = useState("")
  const [state, setState] = useState({ loading: false, error: null, data: null })

  useEffect(() => {
    getOptions().then(setOpts).catch(() => {})
  }, [])

  const programs = (opts && opts.programs) || []

  async function lookup(e) {
    e.preventDefault()
    setState({ loading: true, error: null, data: null })
    try {
      const d = await lookupBenefits(mobile.replace(/\D/g, ""))
      setState({ loading: false, error: null, data: d })
    } catch (err) {
      setState({ loading: false, error: err.message, data: null })
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center p-4 pt-12 gap-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <Link to="/" className="text-muted-foreground text-xs flex items-center gap-1 hover:text-foreground"><ArrowLeft size={14} /> Home</Link>
          <CardTitle className="flex items-center gap-2"><Gift size={18} className="text-primary" /> Benefits &amp; programs</CardTitle>
          <CardDescription>Active barangay assistance programs — and check what you've received.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {programs.length > 0 && (
            <div className="space-y-2">
              {programs.map((p) => (
                <div key={p.id} className="rounded-md border border-border p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{p.name}</span>
                    <Badge variant="secondary">{TYPE_LABEL[p.benefit_type] || p.benefit_type}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                    <CalendarDays size={12} /> {p.start_date} → {p.end_date}
                    {p.barangay && <span>· {p.barangay}</span>}
                    {p.funding_source && <span>· {p.funding_source}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={lookup} className="space-y-3 border-t border-border pt-4">
            <p className="text-sm font-medium">Check benefits you received</p>
            <input required className={inputCls} placeholder="Registered mobile number (09xxxxxxxxx)" inputMode="tel" value={mobile} onChange={(e) => setMobile(e.target.value)} />
            <Button type="submit" className="w-full" disabled={state.loading}>
              {state.loading ? <Loader2 className="animate-spin" size={18} /> : "Check"}
            </Button>
          </form>

          {state.error && <p className="text-sm text-destructive">{state.error}</p>}

          {state.data && (
            <div className="space-y-2">
              {state.data.benefits.length === 0 ? (
                <p className="text-sm text-muted-foreground">No benefit distributions found for this mobile number.</p>
              ) : state.data.benefits.map((b) => (
                <div key={b.distribution_no} className="rounded-md border border-border p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{b.program}</span>
                    <Badge variant="default">{TYPE_LABEL[b.benefit_type] || b.benefit_type}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {b.distribution_no} · {b.received} · {b.item_details}
                    {b.amount != null && ` · ${peso(b.amount)}`}
                    {b.quantity > 1 && ` · qty ${b.quantity}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
