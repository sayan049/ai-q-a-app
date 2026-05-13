import { useFileStore } from '../../store/fileStore'
import { useChatStore } from '../../store/chatStore'
import FileCard from './FileCard'
import LoadingSpinner from '../common/LoadingSpinner'
import { FileText } from 'lucide-react'

export default function FileList() {
  const { files, activeFile, setActiveFile, isLoading } = useFileStore()
  const { clearMessages } = useChatStore()

  const handleSelect = (file) => {
    setActiveFile(file)
    clearMessages()
  }

  if (isLoading) {
    return (
      <div className="flex justify-center pt-8">
        <LoadingSpinner />
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center pt-10 px-4 text-center">
        <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-3">
          <FileText size={18} className="text-gray-600" />
        </div>
        <p className="text-gray-600 text-xs">No files uploaded yet</p>
        <p className="text-gray-700 text-[10px] mt-1">
          Click "Upload New File" above
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {files.map((file) => (
        <FileCard
          key={file.id}
          file={file}
          isActive={activeFile?.id === file.id}
          onClick={() => handleSelect(file)}
        />
      ))}
    </div>
  )
}