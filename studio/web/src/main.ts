import {mountPreview} from './preview';
import './style.css';
const unmount=mountPreview(document.querySelector('#app')!);
if(import.meta.hot)import.meta.hot.dispose(unmount);
