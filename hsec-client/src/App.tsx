import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage.tsx";
import AccountPage from "./pages/AccountPage.tsx";
import CameraViewer from "./pages/CameraViewer.tsx";
import DiscoveryPage from "./pages/DiscoveryPage.tsx";

const App = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route index element={<HomePage />} />
                <Route path="account" element={<AccountPage />} />
                <Route path="discover" element={<DiscoveryPage />} />
                <Route path="camera/:cameraId" element={<CameraViewer />} />
                <Route path="*" element={<div>404 Not Found</div>} />
            </Routes>
        </BrowserRouter>
    );
};

export default App;
