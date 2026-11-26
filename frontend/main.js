import React from 'react';
import {createRoot} from 'react-dom/client';
import './ui.js';
import './style.css';
const App=window.makeCulturaApp(React, '/api');
createRoot(document.getElementById('root')).render(React.createElement(App));
