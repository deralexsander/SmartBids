import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js';

const firebaseConfig = {
  apiKey: 'AIzaSyBlCZkRsr39TbPnL3fse3QH-W3oMIv7384',
  authDomain: 'smartbids-e0b99.firebaseapp.com',
  projectId: 'smartbids-e0b99',
  storageBucket: 'smartbids-e0b99.firebasestorage.app',
  messagingSenderId: '958415636156',
  appId: '1:958415636156:web:3859749919a9e9573ab2b9',
  measurementId: 'G-8JED2S96M0',
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { app, auth };
