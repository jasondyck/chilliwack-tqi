import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">
            Chilliwack Transit Quality Index
          </h1>
        </header>
        <main className="max-w-7xl mx-auto p-6">
          <p className="text-gray-600">Dashboard coming soon. Run the pipeline via the API to see results.</p>
        </main>
      </div>
    </QueryClientProvider>
  )
}
