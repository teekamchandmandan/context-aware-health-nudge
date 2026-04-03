interface Props {
  message: string;
  onRetry: () => void;
}

export default function SectionError({ message, onRetry }: Props) {
  return (
    <div className='bg-white rounded-xl border border-red-200 p-6 text-center'>
      <p className='text-gray-700 mb-3'>{message}</p>
      <button
        onClick={onRetry}
        className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors'
      >
        Try again
      </button>
    </div>
  );
}
