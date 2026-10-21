import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { verifyDoc } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ShieldCheck, ShieldAlert, ShieldX, Loader2 } from "lucide-react"

export default function VerifyPage() {
  const { serial } = useParams()
  const [state, setState] = useState({ loading: true, error: null, data: null })

  useEffect(() => {
    verifyDoc(serial)
      .then((data) => setState({ loading: false, error: null, data }))
      .catch((e) => setState({ loading: false, error: e.message, data: null }))
  }, [serial])

  if (state.loading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={40} />
      </div>
    )

  const d = state.data
  const valid = d && d.valid && !d.expired

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          {valid ? (
            <ShieldCheck className="mx-auto text-success" size={56} />
          ) : d && d.expired ? (
            <ShieldAlert className="mx-auto text-warning" size={56} />
          ) : (
            <ShieldX className="mx-auto text-destructive" size={56} />
          )}
          <CardTitle className="mt-3">
            {state.error ? "Verification unavailable" : valid ? "Authentic document" : d && d.expired ? "Document expired" : "Not a valid document"}
          </CardTitle>
          <CardDescription>
            {valid
              ? "This document was issued by Barangay Poblacion, San Fabian, Pangasinan."
              : d && d.expired
              ? "This document was issued but is past its validity date."
              : "This serial was not found in the barangay registry. If you believe this is an error, visit the barangay hall."}
          </CardDescription>
        </CardHeader>
        {d && (d.valid || d.expired) && (
          <CardContent className="text-left space-y-4">
            <div className="flex justify-center"><Badge variant={valid ? "success" : "warning"}>{d.document_type}</Badge></div>
            <div className="grid grid-cols-2 gap-y-1 text-sm">
              <span className="text-muted-foreground">Serial no.</span><span className="font-mono">{d.serial_no}</span>
              <span className="text-muted-foreground">Issued to</span><span>{d.holder}</span>
              <span className="text-muted-foreground">Issued</span><span>{d.issued}</span>
              <span className="text-muted-foreground">Valid until</span><span>{d.valid_until || "—"}</span>
            </div>
          </CardContent>
        )}
      </Card>
      <Link to="/" className="mt-6"><Button variant="ghost" size="sm">BIS Portal</Button></Link>
    </div>
  )
}
