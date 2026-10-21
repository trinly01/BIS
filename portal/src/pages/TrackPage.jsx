import { useEffect, useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { trackRequest } from "@/lib/api"
import { JOURNEY, STATUS_LABEL, STATUS_DESC, statusVariant } from "@/lib/status"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Check, Circle, Loader2, ArrowLeft, FileText } from "lucide-react"

const inputCls =
  "w-full h-11 rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"

const peso = (n) => (n == null ? null : "₱" + Number(n).toFixed(2))

function LookupForm() {
  const [ref, setRef] = useState("")
  const [phone, setPhone] = useState("")
  const navigate = useNavigate()

  function submit(e) {
    e.preventDefault()
    const r = ref.trim().toUpperCase()
    const p = phone.replace(/\D/g, "")
    if (r && p) navigate(`/track/${r}/${p}`)
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <Link to="/" className="text-muted-foreground text-xs flex items-center gap-1 hover:text-foreground"><ArrowLeft size={14} /> Home</Link>
        <CardTitle>Track a request</CardTitle>
        <CardDescription>
          Enter your request number (e.g. DOC-2026-0001) and the mobile number you used.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4">
          <input className={inputCls + " font-mono uppercase placeholder:normal-case"} placeholder="DOC-2026-0001" value={ref} onChange={(e) => setRef(e.target.value)} />
          <input className={inputCls} placeholder="Mobile number" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Button type="submit" className="w-full" size="lg">Track</Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default function TrackPage() {
  const { ref, key } = useParams()
  const [state, setState] = useState({ loading: true, error: null, data: null })

  useEffect(() => {
    if (!ref || !key) return
    setState({ loading: true, error: null, data: null })
    trackRequest(ref, key)
      .then((data) => setState({ loading: false, error: data ? null : "notfound", data }))
      .catch((e) => setState({ loading: false, error: e.message, data: null }))
  }, [ref, key])

  if (!ref || !key)
    return <div className="min-h-screen flex flex-col items-center justify-center p-4"><LookupForm /></div>

  if (state.loading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={40} />
      </div>
    )

  if (state.error || !state.data)
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
        <div className="text-3xl font-black mb-2"><span className="text-primary">BIS</span> Portal</div>
        <p className="text-muted-foreground mb-6">
          We couldn't find that request. Check the request number and the
          mobile number used when submitting.
        </p>
        <Link to="/track"><Button variant="outline">Back to lookup</Button></Link>
      </div>
    )

  const d = state.data
  const currentIdx = JOURNEY.indexOf(d.status)
  const isException = d.status === "cancelled" || d.status === "rejected"

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="text-2xl font-black tracking-tight">
          <span className="text-primary">BIS</span> Portal
        </div>
        <Badge variant={statusVariant(d.status)}>{STATUS_LABEL[d.status] || d.status}</Badge>
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileText size={18} className="text-primary" /> {d.document_type}</CardTitle>
          <CardDescription className="font-mono">{d.request_no}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-y-1 text-sm">
            <span className="text-muted-foreground">Requested</span><span>{d.requested}</span>
            <span className="text-muted-foreground">Target release</span><span>{d.due_date || "—"}</span>
            <span className="text-muted-foreground">Fee</span><span>{peso(d.fee)}</span>
            {d.or_number && <><span className="text-muted-foreground">OR number</span><span className="font-mono">{d.or_number}</span></>}
            {d.issued && <><span className="text-muted-foreground">Issued</span><span>{d.issued}</span></>}
            {d.valid_until && <><span className="text-muted-foreground">Valid until</span><span>{d.valid_until}</span></>}
            {d.serial_no && <><span className="text-muted-foreground">Serial no.</span><span className="font-mono">{d.serial_no}</span></>}
            {d.released_to && <><span className="text-muted-foreground">Released to</span><span>{d.released_to}</span></>}
          </div>
        </CardContent>
      </Card>

      {!isException ? (
        <Card>
          <CardContent className="pt-6">
            <ol className="space-y-4">
              {JOURNEY.map((s, i) => {
                const done = i < currentIdx || d.status === "released"
                const current = i === currentIdx && d.status !== "released"
                return (
                  <li key={s} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      {done ? (
                        <Check size={18} className="text-primary" />
                      ) : (
                        <Circle size={18} className={current ? "text-warning" : "text-muted"} />
                      )}
                      {i < JOURNEY.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    <div className={current ? "" : "text-muted-foreground"}>
                      <div className="text-sm font-medium">{STATUS_LABEL[s]}</div>
                      {current && <div className="text-xs text-muted-foreground mt-0.5">{STATUS_DESC[s]}</div>}
                    </div>
                  </li>
                )
              })}
            </ol>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">{STATUS_DESC[d.status]}</CardContent>
        </Card>
      )}

      <p className="text-center mt-6">
        <Link to="/track" className="text-muted-foreground text-xs underline">Track another request</Link>
      </p>
    </div>
  )
}
