import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch'

export default function DocumentViewer({ imageUrl, boxes = [], highlightedField, onFieldClick }) {
  const safeBoxes = Array.isArray(boxes) ? boxes : []

  return (
    <div className="panel overflow-hidden">
      <TransformWrapper initialScale={1} minScale={0.8} maxScale={4} centerOnInit>
        <TransformComponent wrapperClass="!w-full !h-[68vh]">
          <div className="relative inline-block w-full">
            <img alt="document preview" className="block w-full select-none" src={imageUrl || 'https://placehold.co/1200x1600/f4eee5/0a1d2d?text=Preview+not+available'} style={{ backgroundColor: 'var(--background)' }} />
            {safeBoxes.map((box) => {
              const bbox = Array.isArray(box.bbox) ? box.bbox : [box.bbox?.x || 0, box.bbox?.y || 0, box.bbox?.w || 0, box.bbox?.h || 0]
              const fieldName = box.field_name || box.field || box.name || ''
              const isActive = highlightedField === fieldName
              return (
                <button
                  key={`${fieldName}-${bbox[0]}-${bbox[1]}`}
                  className={`absolute transition`}
                  style={{ left: `${bbox[0]}px`, top: `${bbox[1]}px`, width: `${bbox[2]}px`, height: `${bbox[3]}px`, borderWidth: 2, borderStyle: 'solid', borderColor: isActive ? 'var(--accent-cyan)' : 'var(--accent-cyan)', backgroundColor: isActive ? 'rgba(34,211,238,0.12)' : 'transparent' }}
                  title={fieldName}
                  onClick={() => onFieldClick?.(fieldName)}
                />
              )
            })}
          </div>
        </TransformComponent>
      </TransformWrapper>
    </div>
  )
}
