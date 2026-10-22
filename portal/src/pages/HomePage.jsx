import { Link } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { FileText, SearchCheck, QrCode, Landmark } from "lucide-react"

const LINKS = [
  { to: "/request", icon: FileText, title: "Request a document",
    desc: "Barangay clearance, indigency, residency, business permit support and more — submit online, claim at the hall." },
  { to: "/track", icon: SearchCheck, title: "Track a request",
    desc: "Check the status of a document request with your request number and mobile number." },
]

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <div className="text-4xl font-black tracking-tight flex items-center gap-2 justify-center">
          <Landmark className="text-primary" size={36} />
          <span><span className="text-primary">BIS</span> Portal</span>
        </div>
        <p className="text-muted-foreground text-sm mt-1">
          Municipality of San Fabian, Pangasinan
        </p>
      </div>
      <div className="w-full max-w-md space-y-4">
        {LINKS.map((l) => (
          <Link key={l.to} to={l.to}>
            <Card className="hover:border-primary transition-colors cursor-pointer">
              <CardHeader className="flex flex-row items-start gap-4 space-y-0">
                <l.icon className="text-primary mt-1 shrink-0" size={28} />
                <div>
                  <CardTitle>{l.title}</CardTitle>
                  <CardDescription className="mt-1">{l.desc}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
      <p className="text-muted-foreground text-xs mt-8 flex items-center gap-1">
        <QrCode size={14} /> Scan the QR code on a barangay document to verify its authenticity.
      </p>
      <p className="text-muted-foreground text-xs mt-2">© Municipality of San Fabian — BIS Portal</p>
    </div>
  )
}
