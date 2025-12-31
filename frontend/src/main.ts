import { createApp } from 'vue'
import { Buffer } from 'buffer'
import App from './App.vue'
import './style.css'

// Polyfill Buffer for TON libraries
window.Buffer = Buffer

createApp(App).mount('#app')
