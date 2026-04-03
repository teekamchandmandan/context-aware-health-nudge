export default function Spinner() {
  return (
    <div className='flex justify-center py-12'>
      <div
        className='h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin'
        role='status'
      >
        <span className='sr-only'>Loading…</span>
      </div>
    </div>
  );
}
