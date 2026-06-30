import { useState, useEffect } from 'react';
import { Monitor, Info } from 'lucide-react';
import { DESK_LAYOUT } from './layout';

interface Workspace {
  id: number;
  code: string;
  pos_x: number;
  pos_y: number;
  user_name: string | null;
  user_email: string | null;
  user_role: string | null;
  user_area: string | null;
  asset_hostname: string | null;
  asset_ip: string | null;
  asset_status: string | null;
  asset_serial: string | null;
  asset_brand: string | null;
  asset_model: string | null;
  user_id: number | null;
  asset_id: number | null;
}

export default function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState({ users: [], assets: [] });
  const [editForm, setEditForm] = useState({ user_id: '', asset_id: '' });

  const handleEditClick = async () => {
    setIsEditing(true);
    setEditForm({
      user_id: selectedWorkspace?.user_id?.toString() || '',
      asset_id: selectedWorkspace?.asset_id?.toString() || ''
    });
    try {
      const res = await fetch('http://localhost:8000/api/inventory-map/options', { credentials: 'include' });
      const data = await res.json();
      setOptions(data);
    } catch (e) {
      console.error(e);
    }
  };

  // Auto-select Asset when User changes
  useEffect(() => {
    const fetchRecommendation = async () => {
      if (editForm.user_id && editForm.user_id !== '') {
        try {
          const res = await fetch(`http://localhost:8000/api/inventory-map/recommend-asset/${editForm.user_id}`);
          if (res.ok) {
            const data = await res.json();
            if (data.asset_id) {
              setEditForm(prev => ({ ...prev, asset_id: data.asset_id.toString() }));
            }
          }
        } catch (e) {
          console.error("Failed to fetch recommendation", e);
        }
      }
    };
    fetchRecommendation();
  }, [editForm.user_id]);

  const handleSave = async () => {
    if (!selectedWorkspace) return;
    try {
      // Get CSRF token from cookies
      const match = document.cookie.match(new RegExp('(^| )csrf_token=([^;]+)'));
      const csrfToken = match ? match[2] : '';

      const response = await fetch('http://localhost:8000/api/inventory-map/assign', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-csrf-token': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({
          workspace_id: selectedWorkspace.id || null,
          code: selectedWorkspace.code,
          user_id: editForm.user_id ? parseInt(editForm.user_id) : null,
          asset_id: editForm.asset_id ? parseInt(editForm.asset_id) : null
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save assignment');
      }

      // Refresh workspaces
      const res = await fetch('http://localhost:8000/api/inventory-map', { credentials: 'include' });
      const data = await res.json();
      setWorkspaces(data);
      const updated = data.find((w: Workspace) => w.code === selectedWorkspace.code);
      setSelectedWorkspace(updated || null);
      setIsEditing(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    // Fetch initial map data
    fetch('http://localhost:8000/api/inventory-map', { credentials: 'include' })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        setWorkspaces(data);
        setLoading(false);
      })
      .catch(e => {
        console.error("Fetch failed:", e);
        setError("Error de conexión con el servidor (Intranet Backend no responde o CORS)");
        setLoading(false);
      });

    // WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/api/inventory/ws`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status_update') {
        setWorkspaces(prev => prev.map(w => {
          const change = data.changes.find((c: any) => c.ip === w.asset_ip);
          if (change) {
            return { ...w, asset_status: change.status };
          }
          return w;
        }));
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  if (loading) return <div className="text-white flex justify-center items-center h-screen text-2xl font-bold animate-pulse">Cargando Plano...</div>;
  if (error) return <div className="text-red-500 flex flex-col justify-center items-center h-screen text-xl font-bold"><h3>Oops, algo salió mal</h3><p>{error}</p></div>;

  return (
    <div className="relative w-full max-w-6xl mx-auto h-[800px] bg-slate-800 rounded-xl shadow-2xl overflow-hidden border border-slate-700">
      <div className="absolute top-4 left-4 z-10 bg-slate-900/80 p-4 rounded-lg backdrop-blur-md border border-slate-700">
        <h1 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          <Monitor className="text-blue-400" /> Mapa de Activos TI
        </h1>
        <p className="text-sm text-slate-400">Puestos y estado de conectividad en tiempo real.</p>
        <div className="mt-4 flex gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1 text-green-400"><span className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></span> Online</div>
          <div className="flex items-center gap-1 text-red-400"><span className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_8px_#ef4444]"></span> Offline</div>
          <div className="flex items-center gap-1 text-slate-400"><span className="w-3 h-3 rounded-full bg-slate-500"></span> Sin Equipo</div>
        </div>
      </div>

      {/* Map Area */}
      <div className="relative w-full h-[650px] mt-8 bg-[#F8F9FA] rounded-xl overflow-hidden border-2 border-slate-700 mx-auto max-w-5xl text-xs font-bold text-black-dark font-sans shadow-inner">
        {/* Background Rooms */}
        <div className="absolute top-0 left-0 w-[50%] h-[50%] bg-[#FFF2CC] border-r-2 border-b-2 border-black flex items-center justify-center text-amber-900 font-extrabold tracking-widest text-xl opacity-90">CASINO</div>
        
        {/* Left Column Baños/Cocina */}
        <div className="absolute top-[30%] left-0 w-[9%] h-[12%] bg-[#E2F0D9] border-r-2 border-y-2 border-black flex items-center justify-center opacity-90 text-[10px]">BAÑO</div>
        <div className="absolute top-[42%] left-0 w-[9%] h-[12%] bg-[#FCE4D6] border-r-2 border-b-2 border-black flex items-center justify-center opacity-90 text-[10px]">COCINA</div>
        <div className="absolute top-[54%] left-0 w-[9%] h-[14%] bg-[#E2F0D9] border-r-2 border-b-2 border-black flex items-center justify-center opacity-90 text-[10px]">BAÑO</div>
        
        {/* Middle Baño/Locket */}
        <div className="absolute top-[54%] left-[38%] w-[5%] h-[14%] bg-[#E2F0D9] border-2 border-black flex items-center justify-center opacity-90 text-[9px] -rotate-90">BAÑO</div>
        <div className="absolute top-[54%] left-[43%] w-[6%] h-[14%] bg-[#EDEDED] border-y-2 border-r-2 border-black flex items-center justify-center opacity-90 text-[9px]">LOCKET</div>

        {/* Top Right Salas */}
        <div className="absolute top-[5%] left-[56%] w-[25%] h-[6%] bg-[#DDEBF7] flex items-center justify-center opacity-90 text-[#2F5597]">Sala Huerfanos 2do Piso</div>
        <div className="absolute top-[18%] left-[50%] w-[5%] h-[12%] bg-[#E2DDF7] border-2 border-black flex items-center justify-center opacity-90 text-[10px] text-[#2F5597]">SUP.</div>

        {/* Escalera */}
        <div className="absolute top-[48%] left-[72%] w-[27%] h-[12%] bg-[#EAEAEA] border-2 border-black flex items-center justify-center opacity-90 text-[10px]">ESCALERA</div>

        {/* Bottom Right Salas */}
        <div className="absolute top-[75%] left-[72%] w-[9%] h-[6%] bg-[#DDEBF7] flex items-center justify-center opacity-90 text-[10px] text-[#2F5597] text-center leading-tight">SALA<br/>MERCED</div>
        <div className="absolute top-[74%] left-[90%] w-[9%] h-[10%] bg-[#E2DDF7] border-2 border-black flex items-center justify-center opacity-90 text-[10px] text-[#2F5597]">SUP</div>

        {/* Render Desks */}
        {DESK_LAYOUT.map(desk => {
          // Find the matching workspace from DB
          const w = workspaces.find(ws => ws.code === desk.label);
          const hasAsset = w && !!w.asset_hostname;
          const isOnline = w && w.asset_status === 'Activo';
          const isOffline = w && w.asset_status === 'Fuera de Linea';

          let colorClass = "bg-[#D9EAD3] border-black text-[#006600]";
          let glowClass = "";
          let statusIndicator = null;

          if (w) {
            colorClass = "bg-[#B6D7A8] border-black text-black-dark shadow-md cursor-pointer hover:scale-110 transition-transform hover:z-10";
            if (hasAsset) {
              if (isOnline) {
                glowClass = "shadow-[0_0_12px_rgba(34,197,94,0.7)] border-green-600";
                statusIndicator = <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-green-500 border border-white"></span>;
              } else if (isOffline) {
                glowClass = "shadow-[0_0_12px_rgba(239,68,68,0.7)] border-red-600";
                statusIndicator = <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-red-500 border border-white"></span>;
              }
            } else {
              statusIndicator = <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-gray-400 border border-white"></span>;
            }
          } else {
            colorClass = "bg-[#D9EAD3] border-black text-[#006600]/50 opacity-50 cursor-pointer hover:scale-110 transition-transform hover:z-10 hover:bg-[#B6D7A8]";
          }

          return (
            <div 
              key={desk.id}
              onClick={() => { 
                if(w) {
                  setSelectedWorkspace(w);
                } else {
                  setSelectedWorkspace({
                    id: 0, code: desk.label, pos_x: 0, pos_y: 0, 
                    user_name: null, user_email: null, user_role: null, user_area: null, 
                    asset_hostname: null, asset_ip: null, asset_status: null, asset_serial: null, asset_brand: null, asset_model: null, 
                    user_id: null, asset_id: null
                  });
                }
              }}
              className={`absolute flex items-center justify-center w-[8%] h-[7%] border ${colorClass} ${glowClass}`}
              style={{ left: `${desk.left}%`, top: `${desk.top}%` }}
              title={w ? `Puesto ${w.code} - Haz clic para detalles` : `Puesto ${desk.label} (No asignado) - Haz clic para crear`}
            >
              {desk.label}
              {statusIndicator}
            </div>
          );
        })}
      </div>

      {/* Modern Drawer for Details */}
      <div className={`absolute top-0 right-0 h-full w-96 bg-slate-900 shadow-2xl border-l border-slate-700 transform transition-transform duration-300 ease-in-out ${selectedWorkspace ? 'translate-x-0' : 'translate-x-full'}`}>
        {selectedWorkspace && (
          <div className="p-6 h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-white">Puesto {selectedWorkspace.code}</h2>
              <button onClick={() => { setSelectedWorkspace(null); setIsEditing(false); }} className="text-slate-400 hover:text-white transition-colors">
                 <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-6 custom-scrollbar">
              
              {isEditing ? (
                <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-inner space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Usuario Asignado</label>
                    <select 
                      className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                      value={editForm.user_id}
                      onChange={(e) => setEditForm({...editForm, user_id: e.target.value})}
                    >
                      <option value="">-- Sin Asignar --</option>
                      {options.users.map((u: any) => (
                        <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Equipo (Activo IT)</label>
                    <select 
                      className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                      value={editForm.asset_id}
                      onChange={(e) => setEditForm({...editForm, asset_id: e.target.value})}
                    >
                      <option value="">-- Sin Asignar --</option>
                      {options.assets.map((a: any) => (
                        <option key={a.id} value={a.id}>{a.name} ({a.ip})</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button onClick={() => setIsEditing(false)} className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg transition-colors text-sm font-bold">Cancelar</button>
                    <button onClick={handleSave} className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2 rounded-lg transition-colors text-sm font-bold">Guardar</button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Equipo Info */}
                  <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-inner">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Monitor className="w-4 h-4" /> Equipo Asignado</h3>
                    {selectedWorkspace.asset_hostname ? (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-slate-400 text-sm">Hostname</span>
                          <span className="text-slate-100 font-mono text-sm">{selectedWorkspace.asset_hostname}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400 text-sm">IP</span>
                          <span className="text-blue-400 font-mono text-sm">{selectedWorkspace.asset_ip}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400 text-sm">Estado</span>
                          <span className={`px-2 py-1 text-xs font-bold rounded-full ${selectedWorkspace.asset_status === 'Activo' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {selectedWorkspace.asset_status === 'Activo' ? 'Online' : 'Offline'}
                          </span>
                        </div>
                        {(selectedWorkspace.asset_brand || selectedWorkspace.asset_model) && (
                          <div className="flex justify-between">
                            <span className="text-slate-400 text-sm">Hardware</span>
                            <span className="text-slate-300 text-sm">{selectedWorkspace.asset_brand} {selectedWorkspace.asset_model}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 italic">No hay equipo asignado a este puesto.</p>
                    )}
                  </div>

                  {/* Usuario Info */}
                  <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-inner">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Info className="w-4 h-4" /> Usuario Asignado</h3>
                    {selectedWorkspace.user_name ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
                              {selectedWorkspace.user_name.charAt(0)}
                            </div>
                            <div>
                              <p className="text-white font-semibold">{selectedWorkspace.user_name}</p>
                              <p className="text-slate-400 text-xs">{selectedWorkspace.user_role}</p>
                            </div>
                        </div>
                        {selectedWorkspace.user_email && (
                          <div className="flex justify-between">
                            <span className="text-slate-400 text-sm">Email</span>
                            <span className="text-slate-300 text-sm">{selectedWorkspace.user_email}</span>
                          </div>
                        )}
                        {selectedWorkspace.user_area && (
                          <div className="flex justify-between">
                            <span className="text-slate-400 text-sm">Área</span>
                            <span className="text-slate-300 text-sm">{selectedWorkspace.user_area}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 italic">No hay usuario asignado a este puesto.</p>
                    )}
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-700">
                    <button onClick={handleEditClick} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors flex justify-center items-center gap-2">
                      Editar Asignación
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
