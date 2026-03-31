import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/reception" element={<Reception />} />
          <Route path="/kitchen" element={<Kitchen />} />
          <Route path="/customer" element={<Customer />} />
        </Routes>
      </div>
    </Router>
  );
}

function Home() {
  return <h1>Welcome to TableZ</h1>;
}

function Reception() {
  return <h1>Reception Dashboard</h1>;
}

function Kitchen() {
  return <h1>Kitchen Dashboard</h1>;
}

function Customer() {
  return <h1>Customer App</h1>;
}

export default App;
