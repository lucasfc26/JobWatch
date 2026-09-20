import { Body, Controller, Get, Param, Post, Res, UseGuards } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import type { Response } from 'express';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { WarehouseFiltersDto } from '../searches/dto/warehouse-filters.dto';
import { ExtractorService } from './extractor.service';

@ApiTags('extractor')
@ApiBearerAuth()
@SkipThrottle()
@UseGuards(JwtAuthGuard)
@Controller('extractor/runs')
export class ExtractorController {
  constructor(private readonly extractor: ExtractorService) {}

  @Post()
  start(@Body() filters: WarehouseFiltersDto) {
    return this.extractor.startRun(filters);
  }

  @Get('current')
  current() {
    return this.extractor.currentRun();
  }

  @Get(':id')
  get(@Param('id') id: string) {
    return this.extractor.getRun(id);
  }

  @Get(':id/frame')
  async frame(@Param('id') id: string, @Res() res: Response) {
    const image = await this.extractor.getFrame(id);
    res.set({ 'Content-Type': 'image/jpeg', 'Cache-Control': 'no-store' }).send(image);
  }
}
