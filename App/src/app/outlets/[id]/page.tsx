export default async function OutletDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Outlet Detail: {id}</h1>
      {/* Empty Outlet Detail Page */}
    </main>
  );
}
