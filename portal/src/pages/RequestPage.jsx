import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getOptions, submitRequest } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, CheckCircle2, ArrowLeft } from "lucide-react"
import SearchableSelect from "@/components/SearchableSelect"

const inputCls =
  "w-full h-11 rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"

const peso = (n) => (n == null ? null : "₱" + Number(n).toFixed(2))

export default function RequestPage() {
  const [opts, setOpts] = useState(null)
  const [form, setForm] = useState({ first_name: "", middle_name: "", last_name: "", mobile: "", barangay: "", document_type: "", purpose: "" })
  const [state, setState] = useState({ loading: false, error: null, result: null })

  useEffect(() => {
    getOptions()
      .then(setOpts)
      .catch((e) => setState((s) => ({ ...s, error: e.message })))
  }, [])

  const types = opts && opts.types
  const barangays = (opts && opts.barangays) || []

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const selected = types && types.find((t) => t.id === form.document_type)

  async function submit(e) {
    e.preventDefault()
    if (!form.barangay) { setState((s) => ({ ...s, error: "Please select your barangay" })); return }
    setState({ loading: true, error: null, result: null })
    try {
      const r = await submitRequest(form)
      if (!r || !r.ok) throw new Error("Submission failed — please try again")
      setState({ loading: false, error: null, result: r })
    } catch (err) {
      setState({ loading: false, error: err.message, result: null })
    }
  }

  if (state.result) {
    const r = state.result
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardHeader>
            <CheckCircle2 className="mx-auto text-success" size={48} />
            <CardTitle className="mt-2">Request received</CardTitle>
            <CardDescription>Present this reference at the barangay hall</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-2xl font-mono font-bold text-primary">{r.request_no}</div>
            <div className="text-sm text-muted-foreground">
              {r.document_type} · Fee {peso(r.fee)} · ETA {r.eta}
            </div>
            <Link to={`/track/${r.request_no}/${form.mobile.replace(/\D/g, "")}`}>
              <Button className="w-full" size="lg">Track this request</Button>
            </Link>
            <Link to="/"><Button variant="ghost" className="w-full">Back to home</Button></Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <Link to="/" className="text-muted-foreground text-xs flex items-center gap-1 hover:text-foreground"><ArrowLeft size={14} /> Home</Link>
          <CardTitle>Request a document</CardTitle>
          <CardDescription>
            Fill out the form — your request enters the barangay queue immediately.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {types === null && !state.error ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-primary" size={32} /></div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <SearchableSelect
                placeholder="Select your barangay"
                value={form.barangay}
                onChange={(id) => setForm((f) => ({ ...f, barangay: id }))}
                items={barangays.map((b) => ({ id: b.id, label: b.name, sub: b.municipality }))}
              />

              <select required className={inputCls} value={form.document_type} onChange={set("document_type")}>
                <option value="" disabled>Select document type</option>
                {(types || []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} — {peso(t.fee)} · ~{t.sla_days} day{t.sla_days === 1 ? "" : "s"}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input required className={inputCls} placeholder="First name" value={form.first_name} onChange={set("first_name")} />
                <input required className={inputCls} placeholder="Last name" value={form.last_name} onChange={set("last_name")} />
              </div>
              <input className={inputCls} placeholder="Middle name (optional)" value={form.middle_name} onChange={set("middle_name")} />
              <input required className={inputCls} placeholder="Mobile number (09xxxxxxxxx)" inputMode="tel" value={form.mobile} onChange={set("mobile")} />
              <textarea required rows={3} className={inputCls + " h-auto py-2"} placeholder="Purpose (e.g. employment requirement)" value={form.purpose} onChange={set("purpose")} />
              {selected && (
                <div className="text-xs text-muted-foreground flex items-center gap-2">
                  <Badge variant="secondary">Fee {peso(selected.fee)}</Badge>
                  <Badge variant="secondary">Valid ~{selected.validity_days} days</Badge>
                </div>
              )}
              {state.error && <p className="text-sm text-destructive">{state.error}</p>}
              <Button type="submit" className="w-full" size="lg" disabled={state.loading}>
                {state.loading ? <Loader2 className="animate-spin" size={18} /> : "Submit request"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
      <p className="text-muted-foreground text-xs mt-6">
        Your name and mobile are used only to process and track this request.
      </p>
    </div>
  )
}
