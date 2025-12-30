export const Loader = ({ size = 'medium', text = '' }) => {
    const sizeClasses = {
      small: 'w-4 h-4 border-2',
      medium: 'w-8 h-8 border-3',
      large: 'w-12 h-12 border-4',
    };
  
    return (
      <div className="flex flex-col items-center justify-center gap-2">
        <div
          className={`
            ${sizeClasses[size]}
            border-gray-300 border-t-primary-600 
            rounded-full animate-spin
          `}
        />
        {text && <p className="text-sm text-gray-600">{text}</p>}
      </div>
    );
  };