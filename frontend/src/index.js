import ReactDom from "react-dom/client";
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import {Provider} from "react-redux"
import { store, persistor } from './stores/store'
import { PersistGate } from 'redux-persist/integration/react';
const appRoot = ReactDom.createRoot(document.getElementById("root"));

appRoot.render(<Provider store={store}><PersistGate loading={null} persistor={persistor}><App/></PersistGate></Provider>, document.getElementById("root"));

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
