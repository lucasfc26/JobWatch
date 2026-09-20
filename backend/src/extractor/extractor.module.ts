import { Module } from '@nestjs/common';
import { ExtractorController } from './extractor.controller';
import { ExtractorService } from './extractor.service';

@Module({
  controllers: [ExtractorController],
  providers: [ExtractorService],
})
export class ExtractorModule {}
