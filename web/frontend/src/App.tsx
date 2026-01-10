import { useState, useEffect } from 'react'

interface Server {
    id: number
    name: string
    type: string
    version: string
    is_running: boolean
    port: number
}

function App() {
    const [servers, setServers] = useState<Server[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchServers()
    }, [])

    const fetchServers = async () => {
        try {
            const res = await fetch('/api/v1/servers')
            const data = await res.json()
            setServers(data)
        } catch (error) {
            console.error('Failed to fetch servers', error)
        } finally {
            setLoading(false)
        }
    }

    const handleStart = async (id: number) => {
        await fetch(`/api/v1/servers/${id}/start`, { method: 'POST' })
        fetchServers()
    }

    const handleStop = async (id: number) => {
        await fetch(`/api/v1/servers/${id}/stop`, { method: 'POST' })
        fetchServers()
    }

    return (
        <div className="min-h-screen bg-background p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold mb-8">Minecraft Server Manager</h1>

                {loading ? (
                    <div>Loading...</div>
                ) : (
                    <div className="grid gap-4">
                        {servers.map((server) => (
                            <div key={server.id} className="p-4 border rounded-lg flex items-center justify-between bg-card">
                                <div>
                                    <h3 className="text-xl font-semibold">{server.name}</h3>
                                    <p className="text-muted-foreground">{server.type} {server.version} : {server.port}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className={`px-2 py-1 rounded text-sm ${server.is_running ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                        {server.is_running ? 'Running' : 'Stopped'}
                                    </span>
                                    {server.is_running ? (
                                        <button
                                            onClick={() => handleStop(server.id)}
                                            className="px-4 py-2 bg-destructive text-destructive-foreground rounded hover:opacity-90"
                                        >
                                            Stop
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => handleStart(server.id)}
                                            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:opacity-90"
                                        >
                                            Start
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}

                        {servers.length === 0 && (
                            <div className="text-center py-12 text-muted-foreground">
                                No servers found. Use the CLI to create one.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

export default App
