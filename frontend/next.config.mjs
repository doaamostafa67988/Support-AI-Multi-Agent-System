/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove the hardcoded IP from allowedDevOrigins — it breaks deployment elsewhere.
  // Next.js allows localhost by default; add your staging domain here when needed.
};

export default nextConfig; // 💡 تم التحديث إلى صيغة ES Module المدعومة
