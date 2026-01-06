// Firestore Database Service for FitFact
// Handles all database operations with Firebase Firestore

import { 
  collection, 
  doc, 
  getDoc, 
  getDocs, 
  setDoc, 
  updateDoc, 
  deleteDoc, 
  addDoc,
  query, 
  where, 
  orderBy, 
  limit,
  serverTimestamp,
  arrayUnion
} from 'firebase/firestore'
import { db } from './firebase'

// ==================== USERS ====================

export async function createOrUpdateUser(user) {
  const userRef = doc(db, 'users', user.uid)
  const userSnap = await getDoc(userRef)
  
  if (userSnap.exists()) {
    // Update existing user
    await updateDoc(userRef, {
      lastLogin: serverTimestamp(),
      loginCount: (userSnap.data().loginCount || 0) + 1,
      displayName: user.displayName || userSnap.data().displayName,
      photoURL: user.photoURL || userSnap.data().photoURL,
    })
    return { ...userSnap.data(), uid: user.uid }
  } else {
    // Create new user
    const newUser = {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName || user.email?.split('@')[0] || 'User',
      photoURL: user.photoURL || null,
      authProvider: user.providerData?.[0]?.providerId || 'email',
      createdAt: serverTimestamp(),
      lastLogin: serverTimestamp(),
      loginCount: 1,
      totalQueries: 0,
      accountType: 'free',
      preferences: {
        theme: 'dark',
        showCitations: true,
        experienceLevel: 'intermediate'
      }
    }
    await setDoc(userRef, newUser)
    return newUser
  }
}

export async function getUser(uid) {
  const userRef = doc(db, 'users', uid)
  const userSnap = await getDoc(userRef)
  return userSnap.exists() ? { ...userSnap.data(), uid } : null
}

export async function updateUserPreferences(uid, preferences) {
  const userRef = doc(db, 'users', uid)
  await updateDoc(userRef, { preferences })
}

export async function incrementUserQueries(uid) {
  const userRef = doc(db, 'users', uid)
  const userSnap = await getDoc(userRef)
  if (userSnap.exists()) {
    await updateDoc(userRef, {
      totalQueries: (userSnap.data().totalQueries || 0) + 1
    })
  }
}

// ==================== CONVERSATIONS ====================

export async function getConversations(uid) {
  const convosRef = collection(db, 'users', uid, 'conversations')
  const q = query(convosRef, orderBy('updatedAt', 'desc'), limit(50))
  const snapshot = await getDocs(q)
  return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
}

export async function createConversation(uid, title = 'New conversation') {
  const convosRef = collection(db, 'users', uid, 'conversations')
  const newConvo = {
    title,
    messages: [],
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp()
  }
  const docRef = await addDoc(convosRef, newConvo)
  return { id: docRef.id, ...newConvo }
}

export async function updateConversation(uid, convoId, data) {
  const convoRef = doc(db, 'users', uid, 'conversations', convoId)
  await updateDoc(convoRef, {
    ...data,
    updatedAt: serverTimestamp()
  })
}

export async function addMessageToConversation(uid, convoId, message) {
  const convoRef = doc(db, 'users', uid, 'conversations', convoId)
  await updateDoc(convoRef, {
    messages: arrayUnion({
      ...message,
      timestamp: Date.now()
    }),
    updatedAt: serverTimestamp()
  })
}

export async function deleteConversation(uid, convoId) {
  const convoRef = doc(db, 'users', uid, 'conversations', convoId)
  await deleteDoc(convoRef)
}

// ==================== QUERY HISTORY ====================

export async function addQueryToHistory(uid, queryData) {
  const historyRef = collection(db, 'users', uid, 'queryHistory')
  const newQuery = {
    ...queryData,
    createdAt: serverTimestamp()
  }
  const docRef = await addDoc(historyRef, newQuery)
  
  // Increment user query count
  await incrementUserQueries(uid)
  
  return { id: docRef.id, ...newQuery }
}

export async function getQueryHistory(uid, limitCount = 50) {
  const historyRef = collection(db, 'users', uid, 'queryHistory')
  const q = query(historyRef, orderBy('createdAt', 'desc'), limit(limitCount))
  const snapshot = await getDocs(q)
  return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
}

// ==================== CACHED RESPONSES ====================

export async function getCachedResponse(queryHash) {
  const cacheRef = doc(db, 'cache', queryHash)
  const cacheSnap = await getDoc(cacheRef)
  return cacheSnap.exists() ? cacheSnap.data() : null
}

export async function setCachedResponse(queryHash, data) {
  const cacheRef = doc(db, 'cache', queryHash)
  await setDoc(cacheRef, {
    ...data,
    createdAt: serverTimestamp(),
    hitCount: 0
  })
}

export async function incrementCacheHit(queryHash) {
  const cacheRef = doc(db, 'cache', queryHash)
  const cacheSnap = await getDoc(cacheRef)
  if (cacheSnap.exists()) {
    await updateDoc(cacheRef, {
      hitCount: (cacheSnap.data().hitCount || 0) + 1,
      lastHit: serverTimestamp()
    })
  }
}

// ==================== PAPERS ====================

export async function savePaper(paperData) {
  const paperRef = doc(db, 'papers', paperData.pmid)
  const paperSnap = await getDoc(paperRef)
  
  if (!paperSnap.exists()) {
    await setDoc(paperRef, {
      ...paperData,
      createdAt: serverTimestamp()
    })
  }
  return paperData.pmid
}

export async function getPaper(pmid) {
  const paperRef = doc(db, 'papers', pmid)
  const paperSnap = await getDoc(paperRef)
  return paperSnap.exists() ? paperSnap.data() : null
}

// ==================== HELPER FUNCTIONS ====================

export function hashQuery(query) {
  // Simple hash function for caching
  let hash = 0
  const normalized = query.toLowerCase().trim()
  for (let i = 0; i < normalized.length; i++) {
    const char = normalized.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return `q_${Math.abs(hash).toString(36)}`
}
