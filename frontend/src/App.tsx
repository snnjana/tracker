import Home from './pages/Home';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Incident Timeline Correlator</h1>
        <p className="subtitle">
          Correlate GitHub commits with AWS CloudWatch data to identify incident root causes
        </p>
      </header>
      <main>
        <Home />
      </main>
    </div>
  );
}

export default App;
