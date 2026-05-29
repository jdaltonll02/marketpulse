export default function LoadingSpinner({ message = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      <div className="w-8 h-8 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin mb-3" />
      <p className="text-sm">{message}</p>
    </div>
  );
}
