import { NativeCamera } from 'travelmind-frontend'

/** Der Auslöser, wie er unter dem Foto-Feld eines Tagebucheintrags steht. */
export const Standard = () => <NativeCamera onPhotoTaken={() => {}} />

/** Gesperrt, solange noch ein Upload läuft. */
export const Gesperrt = () => <NativeCamera onPhotoTaken={() => {}} disabled />
