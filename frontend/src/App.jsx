import { useState } from 'react';
import { UserView } from './components/UserView';
import { AdminView } from './components/AdminView';
import { ShieldCheck } from 'lucide-react';

function App() {
  const [view, setView] = useState('user'); // 'user' or 'admin'
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [requestPayload, setRequestPayload] = useState(null);

  return (
    <div className="min-h-screen flex flex-col font-sans bg-slate-950 text-slate-200">
      <header className="bg-slate-900 border-b border-slate-800 p-4 sticky top-0 z-10 flex justify-between items-center shadow-md">
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-cyan-400 font-bold text-xl tracking-tight">
            <ShieldCheck size={28} className="text-cyan-500" />
            ControlPlane.ai
          </div>
          <div className="text-xs text-slate-500 font-medium tracking-wide mt-1 ml-9">Enterprise AI Runtime Control Layer</div>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => setView('user')}
            className={`px-5 py-2 rounded-md font-medium transition-colors ${view === 'user' ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-500/50' : 'text-slate-400 hover:bg-slate-800'}`}
          >
            User View
          </button>
          <button 
            onClick={() => setView('admin')}
            className={`px-5 py-2 rounded-md font-medium transition-colors ${view === 'admin' ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/50' : 'text-slate-400 hover:bg-slate-800'}`}
          >
            Admin View
          </button>
        </div>
      </header>

      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto w-full">
        {view === 'user' ? (
          <UserView 
            loading={loading} 
            setLoading={setLoading} 
            response={response} 
            setResponse={setResponse}
            error={error}
            setError={setError}
            setRequestPayload={setRequestPayload}
          />
        ) : (
          <AdminView 
            loading={loading} 
            response={response} 
            requestPayload={requestPayload} 
          />
        )}
      </main>
    </div>
  );
}

export default App;
