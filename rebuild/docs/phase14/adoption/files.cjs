'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function classify(p){
 if(typeof p!=='string'||!p||p.includes('\\')||p.includes(':')||path.posix.isAbsolute(p)||p.split('/').some(x=>!x||x==='.'||x==='..'||/[ .]$/.test(x)))throw Error('path_refused');
 return p.split('/').some(x=>/^\.env(?:\.|$)/i.test(x))&&p!=='rebuild/.env.example'?'private':'ordinary';
}
function safePath(root,p){
 classify(p);let current=path.resolve(root);const r=fs.lstatSync(current);if(r.isSymbolicLink()||!r.isDirectory())throw Error('root_refused');
 const parts=p.split('/');for(let i=0;i<parts.length;i++){current=path.join(current,parts[i]);let s;try{s=fs.lstatSync(current);}catch(e){if(e.code==='ENOENT')return {file:path.resolve(root,...parts),stat:null};throw Error('metadata_unavailable');}if(s.isSymbolicLink()||(i<parts.length-1&&!s.isDirectory()))throw Error('unsafe_path');if(i===parts.length-1)return {file:current,stat:s};}
}
function readAllowed(root,p,allowed,read=fs.readFileSync){
 if(classify(p)==='private')throw Error('private_file_refused');if(!allowed.has(p))throw Error('not_allowlisted');
 const {file,stat}=safePath(root,p);if(!stat||!stat.isFile()||stat.nlink!==1)throw Error('file_type_refused');
 const fd=fs.openSync(file,fs.constants.O_RDONLY| (fs.constants.O_NOFOLLOW||0));try{const now=fs.fstatSync(fd);if(now.dev!==stat.dev||now.ino!==stat.ino||now.nlink!==1)throw Error('file_changed');return read(fd);}finally{fs.closeSync(fd);}
}
function metadata(root,p){const {stat}=safePath(root,p);return stat?{state:'present',size:stat.size,mtimeMs:stat.mtimeMs,mode:stat.mode,ino:stat.ino}:{state:'absent'};}
function transfer(source,target,e,allowed,journal){
 const content=readAllowed(source,e.path,allowed);if(hash(content)!==e.sha256)throw Error('source_mismatch');
 const current=metadata(target,e.path).state==='absent'?null:hash(readAllowed(target,e.path,allowed));
 if(current===e.sha256)return {state:'already_matches',path:e.path};if(current!==e.beforeSha256)throw Error('target_conflict');
 journal({stage:'intent',path:e.path,before:current,after:e.sha256});
 const dest=safePath(target,e.path).file,tmp=dest+'.p14-'+crypto.randomBytes(8).toString('hex')+'.tmp';
 // All product parents must already exist. No directory mirroring or creation.
 let renamed=false,primary;try{fs.writeFileSync(tmp,content,{flag:'wx'});if(hash(fs.readFileSync(tmp))!==e.sha256)throw Error('temporary_write_mismatch');
 const again=metadata(target,e.path).state==='absent'?null:hash(readAllowed(target,e.path,allowed));if(again!==current)throw Error('target_conflict');
 fs.renameSync(tmp,dest);renamed=true;if(hash(readAllowed(target,e.path,allowed))!==e.sha256)throw Error('target_write_mismatch');
 journal({stage:'written',path:e.path,after:e.sha256});return {state:'written',path:e.path};
 }catch(error){primary=error;error.transfer={path:e.path,renamed,persistence:false};throw error;}finally{if(!renamed&&fs.existsSync(tmp)){try{fs.unlinkSync(tmp);}catch{if(primary)primary.transfer.cleanup='temporary_file_retained';else throw Error('temporary_cleanup_failed');}}}
}
module.exports={readAllowed,metadata,hash,transfer,classify,safePath};
