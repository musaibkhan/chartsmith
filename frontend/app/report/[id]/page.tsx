export default function ReportPage({ params }: { params: { id: string } }) {
  return (
    <div style={{ padding: 40, color: "#E6E8EC", background: "#0E1116", minHeight: "100vh" }}>
      <h1>Report {params.id}</h1>
      <p>Shareable report links coming in v0.2.</p>
    </div>
  );
}
