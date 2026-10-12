'use strict';
const fs=require('node:fs'),path=require('node:path');
const {developer,image,manifest,hash,read}=require('./inspect.cjs');
const overlayPath='rebuild/compose.original-notifications.yaml';
function deployment(){const bytes=read(developer,overlayPath),overlaySha256=hash(bytes);if(overlaySha256!=='35afc2f08edc21d370d4000486c47b2e1607a9082d1a76cace940dd74aeb30d6')throw Error('deployment_refused');return {format:1,product:manifest,image,overlayPath,overlaySha256,overlayBase64:bytes.toString('base64')};}
module.exports={deployment};
