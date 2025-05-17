import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import UploadPage from './pages/UploadPage';
import ViewPage from "./pages/ViewPage";
import Navbar from './components/Navbar';

const App: React.FC = () => {
	return (
		<>
			<Navbar />
			<Routes>
				<Route path="/" element={<LandingPage />} />
				<Route path="/upload" element={<UploadPage />} />
				<Route path="/viewer" element={<ViewPage />} />
			</Routes>
		</>
	);
};

export default App;
