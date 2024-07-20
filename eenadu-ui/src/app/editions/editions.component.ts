import { Component, OnInit } from '@angular/core';
import { ApiService } from '../api.service';

@Component({
  selector: 'app-editions',
  templateUrl: './editions.component.html',
  styleUrls: ['./editions.component.css']
})
export class EditionsComponent implements OnInit {
  editions: any[] = [];

  constructor(private apiService: ApiService) { }

  ngOnInit() {
    this.apiService.getEditions().subscribe((data: Object) => {
      this.editions = data as any[];
    });
  }
}
