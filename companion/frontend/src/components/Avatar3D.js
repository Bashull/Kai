import React, { useState, useRef, useEffect } from 'three';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

function Avatar3D() {
  const groupRef = useRef();
  const [animation, setAnimation] = useState('idle');

  useFrame(() => {
    if (groupRef.current) {
      // Idle animation
      groupRef.current.position.y = Math.sin(Date.now() * 0.001) * 0.1;
      groupRef.current.rotation.z = Math.sin(Date.now() * 0.0005) * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Head */}
      <mesh position={[0, 1.5, 0]}>
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial color="#fdbcb4" />
      </mesh>

      {/* Eyes */}
      <mesh position={[-0.12, 1.6, 0.35]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#000" />
      </mesh>
      <mesh position={[0.12, 1.6, 0.35]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#000" />
      </mesh>

      {/* Smile */}
      <mesh position={[0, 1.3, 0.38]}>
        <torusGeometry args={[0.15, 0.03, 8, 16, 0, Math.PI]} />
        <meshStandardMaterial color="#000" />
      </mesh>

      {/* Torso */}
      <mesh position={[0, 0.8, 0]}>
        <boxGeometry args={[0.6, 0.8, 0.4]} />
        <meshStandardMaterial color="#4a90e2" />
      </mesh>

      {/* Left Arm */}
      <mesh position={[-0.5, 1, 0]}>
        <boxGeometry args={[0.2, 0.7, 0.2]} />
        <meshStandardMaterial color="#fdbcb4" />
      </mesh>

      {/* Right Arm */}
      <mesh position={[0.5, 1, 0]}>
        <boxGeometry args={[0.2, 0.7, 0.2]} />
        <meshStandardMaterial color="#fdbcb4" />
      </mesh>

      {/* Legs */}
      <mesh position={[-0.15, 0.1, 0]}>
        <boxGeometry args={[0.2, 0.6, 0.2]} />
        <meshStandardMaterial color="#333" />
      </mesh>
      <mesh position={[0.15, 0.1, 0]}>
        <boxGeometry args={[0.2, 0.6, 0.2]} />
        <meshStandardMaterial color="#333" />
      </mesh>
    </group>
  );
}

export default Avatar3D;
