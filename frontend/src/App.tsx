import Home from './pages/Home';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 AI Incident Investigator</h1>
        <p className="subtitle">
          Investigate GitHub commits and issues to identify incident root causes.
        </p>
      </header>
      <main>
        <Home />
      </main>
    </div>
  );
}

export default App;
