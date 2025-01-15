from TTS.api import TTS
import re
from pathlib import Path
import torch
from typing import List
import logging
import time

xtts_v2_speakers = ['Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski']

class CoquiTTSConverter:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2", device="cpu"):
        """初始化TTS转换器"""
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 初始化TTS
        self.logger.info(f"Loading TTS model: {model_name}")
        self.tts = TTS(model_name).to(device)
        
        # 设置输出目录
        self.output_dir = Path("audio_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # 设置分块大小(字符数)
        self.chunk_size = 500
        
    def preprocess_text(self, text: str) -> List[str]:
        """
        预处理文本内容
        1. 清理markdown标记
        2. 规范化标点符号
        3. 智能分段
        """
        # 清理markdown标记
        text = re.sub(r'\[.*?\]|\(.*?\)|#|`|_|-|\*', '', text)
        
        # 规范化标点符号
        text = re.sub(r'[，,]', '，', text)
        text = re.sub(r'[。.]', '。', text)
        text = re.sub(r'[！!]', '！', text)
        text = re.sub(r'[？?]', '？', text)
        
        # 按句子分段并合并到合适大小
        sentences = re.split(r'([。！？])', text)
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
                
                if len(current_chunk) + len(sentence) > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    current_chunk += sentence
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def convert_chunk(self, text: str, output_file: Path, chunk_index: int = 0) -> bool:
        """转换单个文本块"""
        try:
            temp_file = output_file.parent / f"{output_file.stem}_chunk_{chunk_index}{output_file.suffix}"
            self.tts.tts_to_file(text=text,speaker=xtts_v2_speakers[0], file_path=str(temp_file),language="zh-cn")
            return temp_file
        except Exception as e:
            self.logger.error(f"Error converting chunk {chunk_index}: {e}")
            return None

    def merge_wav_files(self, input_files: List[Path], output_file: Path):
        """合并WAV文件"""
        import wave
        
        with wave.open(str(input_files[0]), 'rb') as first_wav:
            params = first_wav.getparams()
            
        with wave.open(str(output_file), 'wb') as output_wav:
            output_wav.setparams(params)
            
            for input_file in input_files:
                with wave.open(str(input_file), 'rb') as wav:
                    output_wav.writeframes(wav.readframes(wav.getnframes()))

    def convert_markdown_to_speech(self, input_file: str, output_name: str = None):
        """将markdown文件转换为语音"""
        try:
            # 读取输入文件
            self.logger.info(f"Reading input file: {input_file}")
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 预处理文本
            chunks = self.preprocess_text(text)
            self.logger.info(f"Split text into {len(chunks)} chunks")
            
            # 设置输出文件
            output_name = output_name or Path(input_file).stem
            output_file = self.output_dir / f"{output_name}.wav"
            
            # 转换每个文本块
            chunk_files = []
            start_time = time.time()
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Converting chunk {i}/{len(chunks)}")
                chunk_file = self.convert_chunk(chunk, output_file, i)
                if chunk_file:
                    chunk_files.append(chunk_file)
                
            # 合并所有音频文件
            if chunk_files:
                self.logger.info("Merging audio files...")
                self.merge_wav_files(chunk_files, output_file)
                
                # 清理临时文件
                for file in chunk_files:
                    file.unlink()
                    
                elapsed_time = time.time() - start_time
                self.logger.info(f"Conversion completed in {elapsed_time:.2f} seconds")
                self.logger.info(f"Output saved to: {output_file}")
            else:
                self.logger.error("No audio chunks were generated successfully")
                
        except Exception as e:
            self.logger.error(f"Error in conversion process: {e}")
            raise

def main():
    # 使用示例
    converter = CoquiTTSConverter()
    
    # 转换文件列表
    files = [
        ("economist.md", "economist"),
        ("time.md", "time"),
        ("nytimes.md", "nytimes")
    ]
    
    for markdown_file, output_name in files:
        if Path(markdown_file).exists():
            print(f"\nProcessing {markdown_file}...")
            converter.convert_markdown_to_speech(markdown_file, output_name)
        else:
            print(f"File not found: {markdown_file}")
            
            
if __name__ == "__main__":
    main()
