import { useState } from 'react'
import Input from '../components/Input'
import Button from '../components/Button'
import { DataManager } from '../utils/DataManager';
import { useNavigate } from 'react-router-dom';

const  isValidCode = (code: string) => {
    try {
        const binaryStr = atob(code);
        if (binaryStr.length !== 4) return false;
        return [...binaryStr].every(ch => {
            const code = ch.charCodeAt(0);
            return code >= 0 && code <= 255;
        });
    } catch (e) {
        return false;
    }
}

const ConnectToServerPage = () => {
    const navigate = useNavigate();
    const [currCode, setCurrCode] = useState("")
    const [isLoading, setIsLoading] = useState(false)

  return (
    <div className='bg-darkpurple h-full flex flex-col justify-center p-6 gap-4'>
        <p className='text-foreground'>Please Enter the server code</p>
        <Input placeholder='Server Code' onChange={(v:string) => setCurrCode(v)}/>
        <Button text='Connect' isLoading={isLoading} disabled={!isValidCode(currCode)} onClick={()=>{
            setIsLoading(true)
            DataManager.connectToServer(currCode, 2000).then((success)=>{
                setIsLoading(false);
                if (!success) alert("Failed to connect")
                navigate("/")

            })
        }}/>
    </div>
  )
}

export default ConnectToServerPage