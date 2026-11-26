// Example staging script for capture.mjs — adapt the lines marked ADAPT to your app.
// It runs inside the page after the app is ready. KeepsakeLens is already loaded as window.KeepsakeLens.

const app = window.app;                                   // ADAPT: however your app exposes its world
await app.jumpToMoment('rescue');                         // ADAPT: advance the world to the moment's peak and pause it
const subject = app.entity('lena');                       // ADAPT: the main character in the moment
const others = [app.entity('tom').position];              // ADAPT: everyone else who belongs in the picture
const bystanders = app.peopleNear(subject.position, 0.5)  // ADAPT: people who should stay out of it
  .filter(p => p.id !== 'lena' && p.id !== 'tom').map(p => p.position);

const pose = { p: subject.position, q: subject.quaternion };
const shot = KeepsakeLens.faceOnCamera(pose, {
  distance: 0.25, pitch: 0.26, lift: 0.014, offset: 0.75,
  include: others, avoid: bystanders, avoidRadius: 0.04, fov: 0.6,   // fov: match your camera
  frontAxis: [1, 0, 0],
  isValid: pos => app.insideWorld(pos) && !app.insideWater(pos),
});
if (!shot) throw new Error('no valid face-on shot for this moment');
console.log('keepsake: ' + JSON.stringify({ offset: shot.offset, distance: shot.distance, bystanders: shot.bystanders }));
app.setCamera(shot.position, shot.target);                // or app.orbit(shot.yaw, shot.pitch, shot.distance, ...shot.target)
